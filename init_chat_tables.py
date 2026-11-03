from sqlalchemy import inspect

from database import Base,engine
from model import Conversation,ChatMessage

def init_chat_tables():
    Base.metadata.create_all(
        bind = engine,
        tables = [
            Conversation.__table__,
            ChatMessage.__table__
        ],
        checkfirst=True
    )

    inspector = inspect(engine)

    tables = inspector.get_table_names()

    print("当前所有table表",tables)

    assert "conversations" in tables
    assert "chat_message" in tables

    print("对话记录表初始化成功")

if __name__ == "__main__":
    init_chat_tables()