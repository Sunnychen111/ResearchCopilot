# 定义真正的数据表

from datetime import datetime

from sqlalchemy import(
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from database import Base


# documents
class Document(Base):

    # 数据库的实际表名
    __tablename__ = "documents"

    # 论文的唯一 ID
    id:Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # PDF 文件名
    filename: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )

    # 文件SHA256哈希
    sha256: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
        index=True
    )

    file_size : Mapped[int]=mapped_column(
        Integer,
        nullable=False
    )

    # 论文总页数
    page_count : Mapped[int | None] = mapped_column(
        Integer,
        nullable=True
    )

    # 文档处理状态
    """
    uploaded 已上传
    processing 正在解析和入库
    ready 已经可以检索
    failed 解析或入库失败
    """
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="uploaded",
        server_default="uploaded"
    )

    # PDF 在本地的保存路径
    storage_path: Mapped[str] = mapped_column(
        Text,
        nullable = False
    )

    # 创建时间 自动生成
    created_at : Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # ORM 关联关系
    # 一篇论文可以对应多个 Chunk
    chunks : Mapped[list["Chunk"]] = relationship(
        back_populates="document",
        cascade="all,delete-orphan",
        passive_deletes=True
    )

# 第二张表；chunks
class Chunk(Base):
    __tablename__ = "chunks"

    # Chunk 自身的唯一主键
    id:Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    # 外键：用于指向documents表的id
    document_id : Mapped[int] = mapped_column(
        Integer,
        ForeignKey("documents.id",ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # 文本来自PDF第几页
    page_number : Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )

    # 在同一篇论文的Chunk的顺序
    chunk_index:Mapped[int]=mapped_column(
        Integer,
        nullable=False
    )

    # Chunk的实际文本内容
    content:Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    # ORM关联：当前Chunk属于哪篇Document
    document:Mapped["Document"] = relationship(
        back_populates="chunks"
    )

    # 同一篇论文中，不允许出现重复的chunk_index
    __table_args__ = (
        UniqueConstraint(
            "document_id",
            "chunk_index",
            name = "uq_document_chunk_index"
        ),
    )

# 第三章表 对话记录表
class Conversation(Base):
    __tablename__ = "conversations"

    id:Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    title:Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        default="New chat"
    )

    created_at:Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    updated_at : Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate = func.now(),
        nullable=False
    )

    messages:Mapped[list["ChatMessage"]] = relationship(
        back_populates="conversation",
        cascade="all,delete-orphan",
        passive_deletes=True
    )

class ChatMessage(Base):
    __tablename__ = "chat_message"

    id:Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True
    )

    conversation_id : Mapped[int] = mapped_column(
        ForeignKey("conversations.id",ondelete="CASCADE"),
        nullable=False,
        index = True
    )

    role:Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )

    content:Mapped[str] = mapped_column(
        Text,
        nullable=False
    )

    retrieved_docs_json: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    conversation:Mapped["Conversation"] = relationship(
        back_populates="messages"
    )