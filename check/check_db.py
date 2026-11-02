
# check_db.py

from sqlalchemy import text
from database import engine, DB_PATH

print("数据库文件位置：", DB_PATH)

# 使用 database.py 中创建的同一个 engine
with engine.connect() as conn:

    # 1. 测试数据库能否执行 SQL
    result = conn.execute(text("SELECT 1")).scalar()
    print("数据库连接测试：", result)

    # 2. 检查当前连接的外键开关
    enabled = conn.exec_driver_sql(
        "PRAGMA foreign_keys"
    ).scalar()

    print("外键是否开启：", enabled)

    # 3. 检查 chunks 表有没有定义外键
    foreign_keys = conn.exec_driver_sql(
        "PRAGMA foreign_key_list(chunks)"
    ).fetchall()

    print("chunks 表的外键：", foreign_keys)
