
# test_pdf_chunks.py
# 仅解析 PDF 并预览 Chunk，不修改 SQLite

import argparse

from pdf_parser import parse_pdf


def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "pdf_path",
        help="需要测试的 PDF 路径"
    )

    args = parser.parse_args()

    # 使用新版本的 Markdown Chunk 解析器
    chunks = parse_pdf(
        args.pdf_path,
        chunk_size=800
    )

    print("\n========== 检查结果 ==========")

    print("Chunk 总数量：", len(chunks))

    # 检查 Chunk 的长度分布
    lengths = [len(chunk["content"]) for chunk in chunks]

    print("最短 Chunk：", min(lengths))
    print("最长 Chunk：", max(lengths))

    # 检查超过 800 字符的 Chunk
    oversized = [
        chunk for chunk in chunks
        if len(chunk["content"]) > 800
    ]

    print("超过 800 字符的 Chunk：", len(oversized))

    # 查看前两个 Chunk 的结尾
    # 注意：之前只打印了前 500 字符
    for chunk in chunks[:2]:
        print(f"\nChunk {chunk['chunk_index']} 结尾：")
        print(repr(chunk["content"][-150:]))

    # 检查每个 Chunk 的必需字段
    for index, chunk in enumerate(chunks):

        assert chunk["chunk_index"] == index
        assert chunk["page_number"] >= 1
        assert chunk["content"].strip()

    # 打印前 3 个 Chunk
    for chunk in chunks[:3]:

        print(
            f"\nChunk {chunk['chunk_index']}"
            f"｜第 {chunk['page_number']} 页"
        )

        print(chunk["content"][:500])

    print("\nPDF Chunk 解析测试通过！")


if __name__ == "__main__":
    main()
