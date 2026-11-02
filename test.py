
# preview_pdf.py
# 专门查看 PDF 解析结果，不写入数据库

import argparse
from pathlib import Path

from pdf_parser import extract_pdf_pages


def main():

    parser = argparse.ArgumentParser(
        description="预览 PDF 版面解析结果"
    )

    parser.add_argument(
        "pdf_path",
        help="需要检查的 PDF 路径"
    )

    args = parser.parse_args()

    # 调用新版版面解析器
    pages = extract_pdf_pages(args.pdf_path)

    output_lines = []

    for page in pages:

        page_number = page["page_number"]
        content = page["content"]

        output_lines.append(
            f"\n{'=' * 30}\n"
            f"第 {page_number} 页\n"
            f"{'=' * 30}\n"
            f"{content}\n"
        )

        # 只预览前两页，避免终端输出过长
        if page_number <= 2:
            print(f"\n=== 第 {page_number} 页 ===")
            print(content[:1000])

    # 保存整个解析结果为 UTF-8 文件
    output_path = Path("pdf_layout_preview.md")

    output_path.write_text(
        "\n".join(output_lines),
        encoding="utf-8"
    )

    print(f"\n解析预览已保存：{output_path.resolve()}")


if __name__ == "__main__":
    main()
