from sqlalchemy import inspect
from database import engine

with engine.begin() as conn:
    # 获取数据库中documents表的字段名称
    inspector = inspect(conn)
    columns = {
        col["name"]
        for col in inspector.get_columns("documents")
    }

    # 添加PDF原文件存储路径
    if "storage_path" not in columns:
        conn.exec_driver_sql(
            "ALTER TABLE documents "
            "ADD COLUMN storage_path TEXT NOT NULL DEFAULT ''"
        )
        print("已添加: storage_path")

    # 重新读取数据库结构 确认修改后的结果
    inspector = inspect(engine)
    columns = [
        col["name"]
        for col in inspector.get_columns("documents")
    ]

    print("documents 当前字段：", columns)