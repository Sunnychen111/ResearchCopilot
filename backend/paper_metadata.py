# 论文标题与作者自动读取模块

import re 
from pathlib import Path

import pymupdf

# 不应该被识别为论文标题的常见内容
INVALID_TITLE_PATTERNS = (
    r"^(?:abstract|introduction|references|keywords?)$",
    r"^(?:microsoft word|untitled|latex|adobe|acrobat)",
    r"^(?:arxiv|proceedings of|the ieee|ieee/cvf conference)",
    r"^(?:preprint|accepted by|copyright|open access)",
)

def clean(value):
    # 清理多余空白字符

    return re.sub(
        r"\s+", " ", str(value or "")
    ).strip(" \t\r\n-_|")

def clean_author_names(value: str | None) -> str | None:
    if not value:
        return None

    text = clean(value)

    if re.search(r"\banonymous\b", text, flags=re.I):
        return None

     # 2. 删除普通数字和上标数字
    # 同时处理 1、1,2、¹、¹,² 等机构编号
    text = re.sub(
        r"[\d⁰¹²³⁴⁵⁶⁷⁸⁹]+"
        r"(?:\s*,\s*[\d⁰¹²³⁴⁵⁶⁷⁸⁹]+)*",
        "",
        text
    )

    # 3. 删除通讯作者、共同作者标记
    text = re.sub(
        r"[*†‡§#]+",
        "",
        text
    )

    # 4. 将 & 和 and 统一为作者分隔符
    text = re.sub(
        r"\s*(?:&|\band\b)\s*",
        ", ",
        text,
        flags=re.I
    )

    # 5. 统一作者之间的逗号和空格
    text = re.sub(r"\s*,\s*", ", ", text)

    # 6. 清除重复逗号
    text = re.sub(r"(?:,\s*){2,}", ", ", text)

    # 7. 清除首尾残留符号
    text = clean(text).strip(" ,;")

    return text or None

    



def plausible_title(value):
    # 简单判断一段文字是否可能是论文标题

    text = clean(value)

    if not 8 <= len(text) <=300:
        return False

    if "@" in text or "http" in text.lower():
        return False

    if not re.search(r"[a-zA-Z\u4e00-\u9fff]", text):
        return False

    return not any(
        re.search(pattern,text,flags=re.I)
        for pattern in INVALID_TITLE_PATTERNS
    )

def plausible_authors(value):
    """过滤明显不是作者姓名的文字。"""

    text = clean(value)

    if not 3 <= len(text) <= 250:
        return False

    if "@" in text or "http" in text.lower():
        return False

    if text.lower() in {
        "anonymous",
        "unknown",
        "author",
        "authors",
        "admin",
        "administrator",
        "microsoft word",
    }:
        return False

    if re.search(
        r"\b(?:department|university|institute|"
        r"school|laboratory|college|faculty|"
        r"abstract|keywords?|corresponding author|"
        r"equal contribution|arxiv)\b",
        text,
        flags=re.I,
    ):
        return False

    return bool(
        re.search(r"[A-Za-z\u4e00-\u9fff]", text)
    )

def extract_page_lines(page):

    result = []

    page_dict = page.get_text("dict")

    for block in page_dict.get("blocks",[]):
        if block.get("type")!=0:
            continue

        for line in block.get("lines",[]):
            spans = line.get("spans",[])

            text = clean(
                "".join(
                    span.get("text","")
                    for span in spans
                )
            )

            if not text:
                continue

            bbox = line.get(
                "bbox", (0, 0, 0, 0)
            )

            sizes = [
                float(span.get("size", 0))
                for span in spans
            ]

            result.append({
                "text": text,
                "x0": float(bbox[0]),
                "y0": float(bbox[1]),
                "y1": float(bbox[3]),
                "size": max(sizes, default=0),
            })

    # 按照首页文本位置排序
    return sorted(
        result,
        key = lambda item:(
            round(item["y0"]/3),
            item["x0"]
        )
    )

def extract_paper_metadata(
        pdf_path:str|Path
)->dict:

    """
    返回示例：
    {
        "title": "OSTrack: One-Stream Transformer...",
        "authors": "Author A, Author B"
    }
    """

    with pymupdf.open(str(pdf_path)) as pdf:
        if len(pdf) ==0 or pdf.needs_pass:
            raise ValueError("PDF 为空或已加密")

        metadata = pdf.metadata or {}
        pdf_title = clean(metadata.get("title"))
        pdf_authors = clean(metadata.get("author"))

        page = pdf[0]
        height = page.rect.height

        lines = extract_page_lines(page)

        # 寻找标题
        candidates = [
            (index,line)
            for index,line in enumerate(lines)
            if 0.025 * height <= line["y0"] <= 0.60 *height
            and plausible_title(line["text"])
            and line["size"] >=11
        ]

        # 1. 检查首页标题行是否被过滤
        print("\n========== 标题候选诊断 ==========")

        for index, line in enumerate(lines):
            # 只检查页面上半部分中字号 >= 11 的文字
            if (
                0.025 * height <= line["y0"] <= 0.60 * height
                and line["size"] >= 11
            ):
                valid = plausible_title(line["text"])

                print(
                    f"index={index}, "
                    f"size={line['size']:.1f}, "
                    f"valid={valid}, "
                    f"text={line['text'][:100]}"
                )

        # 2. 检查最终候选数量
        print("标题候选数量：", len(candidates))

        if candidates:
            index, heading = max(
                candidates,
                key=lambda item: (
                    item[1]["size"],
                    -item[1]["y0"],
                )
            )

            print("选中的标题行：", heading["text"])

        title = None

        authors = (
            pdf_authors
            if plausible_authors(pdf_authors)
            else None
        )

        title_end_y = None
        title_size = 0

        if candidates:

            # 优先选择字体最大的有效文本行
            index,heading = max(
                candidates,
                key = lambda item:(
                    item[1]["size"],
                    -item[1]["y0"],
                )
            )

            title_parts = [heading["text"]]

            title_end_y = heading["y1"]
            title_size = heading["size"]

            # 合并可能得多行标题
            j = index+1

            while j<len(lines) and len(title_parts) <3:
                line = lines[j]

                if(
                    line["y0"] - title_end_y
                        > max(15, 1.3 * title_size)
                        or line["size"] < 0.86 * title_size
                        or abs(
                            line["x0"] - heading["x0"]
                        ) > 135
                        or not plausible_title(line["text"])
                ):
                    break

                title_parts.append(line["text"])
                title_end_y = line["y1"]

                j +=1

            proposed = clean(" ".join(title_parts))

            if plausible_title(proposed):
                title = proposed

        # 首页标题识别未成功时使用PDF元数据
        if title is None and plausible_title(pdf_title):
            title = pdf_title

        if authors is None and title_end_y is not None:
            for line in lines:

                if line["y0"] <= title_end_y + 1:
                    continue

                if line["y0"] > min(
                    title_end_y + height * 0.16,
                    height * 0.55
                ):
                    break

                if (
                    line["size"] >= 8
                    and line["size"] <= title_size * 1.1
                    and plausible_authors(line["text"])
                ):

                    text = line["text"]

                    if (
                        " " in text
                        or "," in text
                        or re.search(
                            r"[\u4e00-\u9fff]{2,}",
                            text
                        )
                    ):
                        authors = text
                        break

        authors = clean_author_names(authors)

        return {
            "title": title,
            "authors": authors,
        }
            

 