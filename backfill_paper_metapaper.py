
"""
为 ResearchCopilot 中已有的论文补全标题与作者。

默认：仅预览，不写数据库。
真正写入：python backfill_paper_metadata.py --apply

不会修改：
- 原始 PDF
- Chunk
- Embedding
- 已有的非空标题或作者
"""

import argparse
from pathlib import Path

from sqlalchemy import inspect, select

from backend.database import BASE_DIR, DB_PATH, SessionLocal, engine
from backend.model import Document
from backend.paper_metadata import extract_paper_metadata


def find_pdf(storage_path: str) -> Path | None:
    """
    同时兼容两种项目路径：

    backend/uploads/xxx.pdf
    uploads/xxx.pdf

    因为之前项目曾调整目录结构。
    """

    if not storage_path:
        return None

    path = Path(storage_path)

    if path.is_absolute():
        return path if path.is_file() else None

    candidates = [
        BASE_DIR / path,
        BASE_DIR.parent / path,
    ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    return None


def main():

    parser = argparse.ArgumentParser(
        description="补全历史论文标题和作者"
    )

    # 默认仅预览，明确添加 --apply 才写入
    parser.add_argument(
        "--apply",
        action="store_true",
        help="确认将提取结果写入 SQLite"
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="最多检查多少篇文献，适合小规模测试"
    )

    args = parser.parse_args()

    print("数据库位置：", DB_PATH.resolve())
    print("运行模式：", "正式写入" if args.apply else "预览")

    if not DB_PATH.is_file():
        raise SystemExit(
            "数据库文件不存在，请先检查 DB_PATH"
        )

    # 写入之前确认实际数据库已经迁移
    existing_columns = {
        col["name"]
        for col in inspect(engine).get_columns("documents")
    }

    missing_columns = (
        {"title", "authors"} - existing_columns
    )

    if missing_columns:
        raise SystemExit(
            f"数据库缺少字段：{missing_columns}，"
            "请先执行字段迁移"
        )

    processed = 0
    changed = 0
    skipped = 0
    failed = 0

    with SessionLocal() as db:

        stmt = select(Document).order_by(
            Document.id.asc()
        )

        if args.limit is not None:
            if args.limit < 1:
                raise SystemExit("--limit 必须大于 0")
            stmt = stmt.limit(args.limit)

        documents = db.scalars(stmt).all()

        print("读取到论文数量：", len(documents))

        for document in documents:

            # 非空信息不覆盖
            need_title = not (
                document.title or ""
            ).strip()

            need_authors = not (
                document.authors or ""
            ).strip()

            if not need_title and not need_authors:
                skipped += 1
                continue

            pdf_path = find_pdf(
                document.storage_path
            )

            if pdf_path is None:
                print(
                    f"[跳过] ID={document.id} "
                    f"文件不存在：{document.storage_path}"
                )
                skipped += 1
                continue

            processed += 1

            try:
                result = extract_paper_metadata(
                    pdf_path
                )

                new_title = document.title
                new_authors = document.authors

                if need_title and result.get("title"):
                    new_title = result["title"]

                if need_authors and result.get("authors"):
                    new_authors = result["authors"]

                # 判断是否确实补全了字段
                has_change = (
                    new_title != document.title
                    or new_authors != document.authors
                )

                print(
                    f"\nID={document.id} | "
                    f"{document.filename}"
                )

                print("标题：", new_title or "未识别")
                print("作者：", new_authors or "未识别")

                if not has_change:
                    print("结果：没有可补全的信息")
                    continue

                changed += 1

                if args.apply:
                    document.title = new_title
                    document.authors = new_authors

                    db.commit()
                    print("结果：已写入数据库")
                else:
                    print("结果：预览成功，未写入")

            except Exception as exc:
                db.rollback()
                failed += 1

                print(
                    f"[失败] ID={document.id}：{exc}"
                )

    print("\n========== 补全汇总 ==========")
    print("检查论文：", processed)
    print("可补全论文：", changed)
    print("跳过论文：", skipped)
    print("处理失败：", failed)

    if not args.apply:
        print(
            "\n当前为预览模式，"
            "使用 --apply 才会正式写入。"
        )


if __name__ == "__main__":
    main()
