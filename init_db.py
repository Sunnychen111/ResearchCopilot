from sqlalchemy import inspect,text

from database import Base,engine,DB_PATH

import model

def init_database():
    print("开始初始化 ReseachCopilot 数据库")

    Base.metadata.create_all(bind=engine)

    #inspect 可以读取数据库的实际结构
    inspector = inspect(engine)

    print(f"\n数据库位置：{DB_PATH}")

    # 获取数据库中已经存在的表
    tables = inspector.get_table_names()

    print("\n当前数据表：")

    for table_name in tables:
        print(f"\n表名：{table_name}")

        columns = inspector.get_columns(table_name)

        for column in columns:
            print(
                f"  {column['name']} "
                f"({column['type']})"
            )

    with engine.connect() as conn:

        # 使用 SQLAlchemy 执行原生 SQLite 命令
        # scalar_one() 获取结果中唯一的一行一列
        enabled = conn.exec_driver_sql(
            "PRAGMA foreign_keys"
        ).scalar_one()

        # 输出真实返回值和数据类型
        # 用于检查是否存在类型或变量错误
        print("DEBUG 外键返回值：", repr(enabled))
        print("DEBUG 返回类型：", type(enabled))

        # 1 = 开启，0 = 关闭
        if enabled == 1:
            print("外键约束：已开启")
        else:
            print("外键约束：未开启")

if __name__ == "__main__":
    init_database()