
# pdf_parser.py
# ResearchCopilot PDF Parser V2
#
# 功能：
# 1. 自适应解析单栏、双栏和混合布局 PDF
# 2. 按页保存 Markdown 文本
# 3. 清理基础格式噪声
# 4. 切分带重叠的 Chunk
# 5. 保持与现有 SQLite 入库接口兼容

import re
from pathlib import Path

import pymupdf
import pymupdf4llm


def clean_text(text: str) -> str:
    """
    清理 PDF 解析后的基础文本格式。

    特别注意：
    这里不删除 Markdown 标题、段落和空行，
    因为这些信息有助于后续 RAG 理解论文结构。
    """

    # 去掉不可见的空字符
    text = text.replace("\x00", "")

    # 统一换行符
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # 删除每行末尾的多余空格
    # 保留行首缩进，不破坏 Markdown 列表结构
    lines = [
        line.rstrip()
        for line in text.splitlines()
    ]

    text = "\n".join(lines)

    # 连续三个以上换行压缩为两个
    # 保留自然的段落分隔
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def extract_pdf_pages(
    pdf_path: str | Path
) -> list[dict]:
    """
    提取 PDF 每一页的文本。

    返回：
    [
        {
            "page_number": 1,
            "content": "第一页 Markdown 正文"
        },
        ...
    ]

    该函数不执行 Chunk 切分，
    因此可以单独检查解析后的阅读顺序。
    """

    pdf_path = Path(pdf_path)

    # 检查原始 PDF 文件是否存在
    if not pdf_path.is_file():
        raise FileNotFoundError(
            f"PDF 文件不存在：{pdf_path}"
        )

    pages = []

    with pymupdf.open(str(pdf_path)) as pdf:

        # 拒绝尚未解锁的密码保护文件
        if pdf.needs_pass:
            raise ValueError("不支持需要密码的 PDF")

        print(f"PDF 总页数：{pdf.page_count}")

        # PyMuPDF4LLM 执行版面分析
        #
        # page_chunks=True：
        # 返回逐页的数据，方便保留论文页码
        #
        # use_ocr=False：
        # 暂不使用 OCR，避免把本来正常的英文
        # PDF 文本重新识别而产生错误
        #
        # 这里不指定单栏或双栏，
        # 由版面分析器自行恢复阅读顺序
        page_results = pymupdf4llm.to_markdown(
            pdf,
            page_chunks=True,
            use_ocr=False,
            show_progress=False
        )

        # 验证解析结果的基本结构
        if not isinstance(page_results, list):
            raise ValueError(
                "PDF 解析器没有返回逐页结果"
            )

        if len(page_results) != pdf.page_count:
            raise ValueError(
                "解析结果页数与 PDF 页数不一致"
            )

        # 遍历解析后的每一页
        for index, page_data in enumerate(page_results):

            page_number = index + 1

            # 读取当前页的 Markdown 文本
            markdown_text = clean_text(
                page_data.get("text", "")
            )

            # 如果版面分析没有返回文本，
            # 再尝试一次普通 PyMuPDF 提取
            #
            # 这是失败回退机制：
            # 对于部分特殊 PDF，可避免整页直接丢失
            if not markdown_text:

                fallback_text = pdf[index].get_text(
                    "text",
                    sort=True
                )

                if fallback_text.strip():
                    print(
                        f"警告：第 {page_number} 页"
                        "版面解析为空，"
                        "使用基础文本提取回退"
                    )

                    markdown_text = clean_text(
                        fallback_text
                    )

            # 即使当前页为空，也保留页码记录
            # 例如论文中可能存在纯图片页
            pages.append({
                "page_number": page_number,
                "content": markdown_text
            })

            print(
                f"第 {page_number} 页："
                f"提取 {len(markdown_text)} 字符"
            )

    # 所有页面都没有可用文本时，
    # 不应该继续数据库入库
    if not any(page["content"] for page in pages):
        raise ValueError(
            "整篇 PDF 没有可提取文本"
        )

    return pages


def split_text(
    text: str,
    chunk_size: int = 800,
    overlap: int = 120
) -> list[str]:
    """
    将单页文本切成多个 Chunk。

    使用固定正步长，防止之前出现的无限循环
    和 MemoryError 问题。

    chunk_size = 800
    overlap = 120
    每次移动 680 字符。
    """

    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(
            "overlap 必须满足 0 <= overlap < chunk_size"
        )

    if not text:
        return []

    chunks = []

    # 步长始终为正数，不会无限循环
    step = chunk_size - overlap

    for start in range(0, len(text), step):

        end = min(start + chunk_size, len(text))

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        # 到达文本末尾后立即结束
        if end == len(text):
            break

    return chunks


def parse_pdf(
    pdf_path: str | Path,
    chunk_size: int = 800,
    overlap: int = 120
) -> list[dict]:
    """
    PDF 解析入口。

    返回值继续兼容 ingest_pdf.py，
    每个 Chunk 包含：
    page_number、chunk_index、content。
    """

    # 第一步：版面分析与逐页正文提取
    pages = extract_pdf_pages(pdf_path)

    all_chunks = []

    # 第二步：针对每一页切分 Chunk
    for page in pages:

        page_number = page["page_number"]
        page_text = page["content"]

        if not page_text:
            print(f"第 {page_number} 页：跳过空文本")
            continue

        page_chunks = split_text(
            page_text,
            chunk_size=chunk_size,
            overlap=overlap
        )

        # 第三步：生成数据库需要的结构
        for content in page_chunks:

            all_chunks.append({
                "page_number": page_number,

                # 在整篇论文中连续编号
                "chunk_index": len(all_chunks),

                "content": content
            })

        print(
            f"第 {page_number} 页："
            f"生成 {len(page_chunks)} 个 Chunk"
        )

    print(
        f"\nPDF 解析完成，"
        f"总 Chunk 数：{len(all_chunks)}"
    )

    return all_chunks
