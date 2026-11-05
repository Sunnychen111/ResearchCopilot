
"""
ResearchCopilot v0.3
为已有 documents 表增加论文元数据字段。

运行方式（项目根目录）：
python migrate_document_metadata.py
"""

import sqlite3
from datetime import datetime

from sqlalchemy import inspect

from backend.database import DB_PATH, engine


# 需要新增的字段及其 SQLite 类型
NEW_COLUMNS = {
    "title": "TEXT",
    "authors": "TEXT",
    "venue": "TEXT",
    "rank_system": "TEXT",
    "rank_value": "TEXT",
}


def migrate():
    print("数据库路径：", DB_PATH.resolve())

    # 防止意外创建一个空数据库
    if not DB_PATH.is_file():
        raise FileNotFoundError(
            f"数据库不存在：{DB_PATH}"
        )

    # 使用 SQLite 的备份接口进行安全备份
    backup_path = DB_PATH.with_name(
        f"{DB_PATH.stem}_backup_"
        f"{datetime.now():%Y%m%d_%H%M%S}.db"
    )

    with sqlite3.connect(str(DB_PATH)) as src:
        with sqlite3.connect(str(backup_path)) as dst:
            src.backup(dst)

    print("数据库备份完成：", backup_path)

    # 获取当前表结构
    inspector = inspect(engine)

    if not inspector.has_table("documents"):
        raise RuntimeError("未找到 documents 表")

    existing = {
        item["name"]
        for item in inspector.get_columns("documents")
    }

    # 只新增缺失字段
    with engine.begin() as conn:
        for name, sql_type in NEW_COLUMNS.items():

            if name in existing:
                print(f"跳过已有字段：{name}")
                continue

            conn.exec_driver_sql(
                f"ALTER TABLE documents "
                f"ADD COLUMN {name} {sql_type}"
            )

            print(f"新增字段：{name}")

    # 验证最终结构
    inspector = inspect(engine)
    final_columns = {
        col["name"]
        for col in inspector.get_columns("documents")
    }

    missing = set(NEW_COLUMNS) - final_columns

    if missing:
        raise RuntimeError(
            f"迁移不完整：{missing}"
        )

    print("文献元数据字段迁移成功！")


if __name__ == "__main__":
    migrate()
