
# markdown_chunker.py
# Markdown 结构感知切块 V1

import re
import textwrap


def split_markdown_block(text: str) -> list[str]:
    """
    第一步：把 Markdown 拆分成结构块。
    """

    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    blocks = []
    current_lines = []

    def save_block():
        if current_lines:
            block = "\n".join(current_lines).strip()

            if block:
                blocks.append(block)

            current_lines.clear()

    for line in text.splitlines():

        stripped = line.strip()

        # 空行：结束当前结构块
        if not stripped:
            save_block()
            continue

        # 标题单独成为结构块
        if re.match(r"^#{1,6}\s+", stripped):
            save_block()
            blocks.append(stripped)
            continue

        # 判断当前行是否属于 Markdown 表格
        is_table = (
            stripped.startswith("|")
            and stripped.count("|") >= 2
        )

        # 判断缓冲区是否存储着表格
        previous_is_table = (
            bool(current_lines)
            and current_lines[0].lstrip().startswith("|")
        )

        # 表格与正文发生切换时保存当前块
        if current_lines and is_table != previous_is_table:
            save_block()

        # 所有有效文本行都必须加入缓冲区
        current_lines.append(line.rstrip())

    save_block()

    return blocks


def split_long_paragraph(
    text: str,
    max_chars: int
) -> list[str]:
    """
    第二步：拆分超长正文段落。

    处理策略：
    1. 长度符合要求：保持原文不变
    2. 超长段落：优先按句子拆分
    3. 单句仍然过长：再按单词边界拆分
    """

    if len(text) <= max_chars:
        return [text]

    # 尝试根据中英文句末标点分句
    sentences = re.split(
        r"(?<=[。！？!?])\s*|(?<=\.)\s+",
        text.strip()
    )

    units = []

    for sentence in sentences:

        sentence = sentence.strip()

        if not sentence:
            continue

        if len(sentence) <= max_chars:
            units.append(sentence)

        else:
            # 极长句子：使用 textwrap 控制长度
            # 优先按空格拆分，必要时才拆长词
            pieces = textwrap.wrap(
                sentence,
                width=max_chars,
                break_long_words=True,
                break_on_hyphens=False
            )

            units.extend(pieces)

    results = []
    current = ""

    # 将短句重新组合，减少碎片化
    for unit in units:

        candidate = (
            current + " " + unit
            if current else unit
        )

        if current and len(candidate) > max_chars:
            results.append(current)
            current = unit
        else:
            current = candidate

    if current:
        results.append(current)

    return results


def chunk_markdown(
    text: str,
    max_chars: int = 800
) -> list[str]:
    """
    第三步：将 Markdown 结构块合并为 Chunk。

    规则：
    1. 标题作为后续正文的上下文
    2. 多个短正文 Block 可以合并
    3. 超长正文按照句子拆分
    4. 表格尽可能保持完整
    """

    if max_chars < 100:
        raise ValueError(
            "max_chars 不能小于 100"
        )

    blocks = split_markdown_block(text)

    chunks = []

    # 当前章节标题
    heading = ""

    # 当前正在构建的 Chunk
    current = ""

    def save_chunk():
        nonlocal current

        if current.strip():
            chunks.append(current.strip())

        current = ""

    for block in blocks:

        # 1. 处理 Markdown 标题
        is_heading = bool(
            re.match(r"^#{1,6}\s+", block)
        )

        if is_heading:
            save_chunk()

            heading = block
            continue

        # 2. 处理 Markdown 表格
        is_table = (
            block.lstrip().startswith("|")
            and block.count("|") >= 2
        )

        if is_table:
            # 表格独立保存，避免被字符切块截断
            save_chunk()

            table_chunk = (
                heading + "\n\n" + block
                if heading else block
            )

            chunks.append(table_chunk)
            continue

        # 3. 为章节标题预留空间
        available_chars = max(
            50,
            max_chars - len(heading) - 2
        )

        # 4. 长正文先按句子进行切分
        pieces = split_long_paragraph(
            block,
            max_chars=available_chars
        )

        # 5. 把短文本组合成 Chunk
        for piece in pieces:

            # 开始新的 Chunk 时附上章节标题
            prefix = (
                heading + "\n\n"
                if heading else ""
            )

            if current:
                candidate = current + "\n\n" + piece
            else:
                candidate = prefix + piece

            # 如果合并后超过限制，保存前一个 Chunk
            if current and len(candidate) > max_chars:

                save_chunk()

                candidate = prefix + piece

            current = candidate

    # 6. 保存最后一个 Chunk
    save_chunk()

    return chunks


if __name__ == "__main__":

    sample_text = """
## 3. Method

MPDTrack consists of three modules.
The method maintains temporal identity information.

| Method | AUC |
|---|---|
| Baseline | 74.0 |
| Ours | 75.1 |

## 4. Experiments

We evaluate the method on LaSOT.
"""

    # 验证原有 Block 结构识别
    blocks = split_markdown_block(sample_text)

    assert len(blocks) == 5

    print("Block 结构识别通过！")

    # 验证新的 Chunk 合并
    chunks = chunk_markdown(
        sample_text,
        max_chars=200
    )

    print(f"\n共生成 {len(chunks)} 个 Chunk")

    for index, chunk in enumerate(chunks):

        print(f"\n========== Chunk {index} ==========")
        print(chunk)

    # 标题 + 正文形成一个 Chunk
    assert "MPDTrack consists" in chunks[0]

    # 表格应该完整保留
    assert "| Ours | 75.1 |" in chunks[1]

    # 实验章节仍然存在
    assert "## 4. Experiments" in chunks[-1]

    print("\nMarkdown Chunk 合并测试通过！")
