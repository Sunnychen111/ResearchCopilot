from pathlib import Path
from sqlalchemy import create_engine,event

# 创建数据库会话工厂
from sqlalchemy.orm import sessionmaker, DeclarativeBase

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "research.db"

# 配置数据库地址
DATABASE_URL = f"sqlite:///{DB_PATH.as_posix()}"

# 创建数据库引擎
# 是与数据库交互的入口
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread":False},
    echo=False
)

@event.listens_for(engine,"connect")
def enable_foreign_keys(dbapi_connection,connection_record):
    cursor = dbapi_connection.cursor()

    # 启用外键约束，防止chunk引用不存在的论文
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

# 创建数据库会话工厂
SessionLocal = sessionmaker(
    bind = engine,
    autoflush=False,
    expire_on_commit=False
)

# 定义ORM模型几类
class Base(DeclarativeBase):
    pass