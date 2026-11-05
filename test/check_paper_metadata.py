
"""
测试 ResearchCopilot 论文元数据提取

使用方式：
python test/check_paper_metadata.py "PDF文件路径"

只读取 PDF，不修改 SQLite。
"""

import sys
from pathlib import Path

# 允许从项目根目录直接运行此脚本
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pymupdf

from backend.paper_metadata import (
    extract_paper_metadata,
    extract_page_lines,
)


def test_metadata(pdf_path):

    pdf_path = Path(pdf_path)

    if not pdf_path.is_file():
        raise FileNotFoundError(
            f"找不到 PDF：{pdf_path}"
        )

    # 1. 查看实际提取结果
    result = extract_paper_metadata(pdf_path)

    print("\n========== 识别结果 ==========")
    print("文件：", pdf_path.name)
    print("标题：", result["title"])
    print("作者：", result["authors"])

    # 2. 查看 PDF 首页排版信息
    with pymupdf.open(pdf_path) as pdf:

        page = pdf[0]

        print("\n========== PDF 原始元数据 ==========")
        print("Title：", pdf.metadata.get("title"))
        print("Author：", pdf.metadata.get("author"))

        print("\n========== 首页字体信息 ==========")
        print("页面高度：", page.rect.height)

        lines = extract_page_lines(page)

        print(
            f"{'字号':<8}"
            f"{'Y坐标':<10}"
            f"{'文字内容'}"
        )

        print("-" * 90)

        # 只显示首页前 45% 高度中的文字
        for line in lines:

            if line["y0"] > page.rect.height * 0.45:
                continue

            print(
                f"{line['size']:<8.1f}"
                f"{line['y0']:<10.1f}"
                f"{line['text'][:85]}"
            )


if __name__ == "__main__":

    if len(sys.argv) != 2:
        print(
            '用法：python test/check_paper_metadata.py '
            '"论文.pdf"'
        )
        sys.exit(1)

    test_metadata(sys.argv[1])
