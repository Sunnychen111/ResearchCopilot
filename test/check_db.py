
"""
检查 ResearchCopilot 数据库中的论文元数据。

默认显示所有论文。
可以通过 --keyword 过滤论文。

只读取数据库，不会修改任何记录。
"""

import sys
import argparse
from pathlib import Path

from sqlalchemy import select, func

# 将项目根目录加入 Python 导入路径
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.database import (
    DB_PATH,
    SessionLocal,
)

from backend.model import Document, Chunk


def check_database(keyword=None):

    print("=" * 75)
    print("当前数据库：", DB_PATH.resolve())
    print("=" * 75)

    with SessionLocal() as db:

        stmt = select(Document).order_by(
            Document.id.asc()
        )

        if keyword:
            stmt = stmt.where(
                Document.filename.ilike(
                    f"%{keyword}%"
                )
            )

        documents = db.scalars(stmt).all()

        print("查询到的文献数量：", len(documents))

        for doc in documents:

            # 检查这篇论文实际保存了多少 Chunk
            chunk_count = db.scalar(
                select(func.count(Chunk.id))
                .where(Chunk.document_id == doc.id)
            )

            print("\n" + "-" * 75)

            print("ID：", doc.id)
            print("原始文件：", doc.filename)

            print("\n【论文元数据】")
            print("标题：", repr(doc.title))
            print("作者：", repr(doc.authors))

            print("\n【发表信息】")
            print("会议/期刊：", doc.venue)
            print("等级体系：", doc.rank_system)
            print("论文等级：", doc.rank_value)

            print("\n【文件与解析状态】")
            print("状态：", doc.status)
            print("页数：", doc.page_count)
            print("Chunk 数量：", chunk_count)
            print("保存路径：", doc.storage_path)
            print("SHA256：", doc.sha256)

        print("\n" + "=" * 75)
        print("数据库检查完成")


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--keyword",
        type=str,
        default=None,
        help="按照文件名过滤论文",
    )

    args = parser.parse_args()

    check_database(args.keyword)
