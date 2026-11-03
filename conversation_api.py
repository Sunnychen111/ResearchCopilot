import json
import logging

from fastapi import APIRouter
from pydantic import BaseModel,Field
from sqlalchemy import select,func,inspect

from database import SessionLocal
from model import Conversation,ChatMessage

from datetime import datetime,timezone
from fastapi import HTTPException
from openai import OpenAIError

from rag_sqlite import rag_chat


router = APIRouter(
    prefix="/api/conversations",
    tags = ["聊天记录管理"]
)

class CreatConversationRequest(BaseModel):

    title : str = Field(
        default="New Chat",
        max_length = 200
    )

# 将ORM转换为字典
def serialize_conversation(conversation):
    return {
        "id": conversation.id,
        "title": conversation.title,
        "created_at": (
            conversation.created_at.isoformat()
            if conversation.created_at else None
        ),
        "updated_at": (
            conversation.updated_at.isoformat()
            if conversation.updated_at else None
        )
    }

@router.post("",status_code=201)
def create_conversation(
    request: CreatConversationRequest
):
    title = request.title.strip() or "New Chat"

    with SessionLocal() as db:

        conversation = Conversation(
            title = title
        )

        db.add(conversation)
        db.commit()
        # 获取数据库生成时间
        db.refresh(conversation)

        return serialize_conversation(
            conversation
        )

@router.get("")
def list_conversation():

    with SessionLocal() as db:
        stmt = (
            select(Conversation,func.count(ChatMessage.id).label("message_count"))
            .outerjoin(
                ChatMessage,ChatMessage.conversation_id ==Conversation.id
            )
            .group_by(
                Conversation.id
            )
            .order_by(
                Conversation.updated_at.desc(),
                Conversation.id.desc()
            )
        )

        rows = db.execute(stmt).all()
        results = []

        for conversation,message_count in rows:
            item = serialize_conversation(conversation)

            item["message_count"] = message_count

            results.append(item)

        return results

logger = logging.getLogger(__name__)


# 一、定义发送问题的数据结构
class SendMessageRequest(BaseModel):

    question: str = Field(
        min_length=1,
        max_length=2000
    )


# 二、将聊天消息转换为前端需要的 JSON 结构
def serialize_message(message):

    # 从数据库读取历史检索证据
    docs = []

    if message.retrieved_docs_json:
        docs = json.loads(
            message.retrieved_docs_json
        )

    return {
        "id": message.id,
        "role": message.role,
        "text": message.content,
        "docs": docs,
        "created_at": (
            message.created_at.isoformat()
            if message.created_at else None
        )
    }


# 三、发送问题，并保存本轮聊天记录
@router.post("/{conversation_id}/messages")
def send_message(
    conversation_id: int,
    request: SendMessageRequest
):

    question = request.question.strip()

    if not question:
        raise HTTPException(
            status_code=422,
            detail="问题不能为空"
        )

    # 第一步：确认对话存在
    with SessionLocal() as db:

        conversation = db.get(
            Conversation,
            conversation_id
        )

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="聊天话题不存在"
            )

    # 第二步：调用已有的 RAG 问答功能
    # 不在数据库事务中等待 DeepSeek
    try:
        result = rag_chat(question)

    except OpenAIError:
        logger.exception("DeepSeek 请求失败")

        raise HTTPException(
            status_code=502,
            detail="DeepSeek 服务暂时不可用"
        )

    except Exception:
        logger.exception("RAG 问答失败")

        raise HTTPException(
            status_code=500,
            detail="RAG 问答失败"
        )

    # 第三步：提取回答和检索证据
    answer = result.get("answer") or ""
    retrieved_docs = result.get(
        "retrieved_docs"
    ) or []

    # 将检索证据转为 JSON 字符串
    docs_json = json.dumps(
        retrieved_docs,
        ensure_ascii=False
    )

    # 第四步：保存用户问题和 AI 回答
    with SessionLocal() as db:

        # 再次检查对话，防止调用模型期间被删除
        conversation = db.get(
            Conversation,
            conversation_id
        )

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="聊天话题已不存在"
            )

        # 用户消息
        user_message = ChatMessage(
            conversation_id=conversation_id,
            role="user",
            content=question
        )

        # AI 消息
        assistant_message = ChatMessage(
            conversation_id=conversation_id,
            role="assistant",
            content=answer,
            retrieved_docs_json=docs_json
        )

        # 将两条消息加入同一个事务
        db.add_all([
            user_message,
            assistant_message
        ])

        # 更新话题最近使用时间
        conversation.updated_at = datetime.now(
            timezone.utc
        )

        # 提交事务
        db.commit()

        # 获取数据库生成的消息 ID 和时间
        db.refresh(user_message)
        db.refresh(assistant_message)

        return {
            "conversation_id": conversation_id,
            "user_message": serialize_message(
                user_message
            ),
            "assistant_message": serialize_message(
                assistant_message
            )
        }


# 四、获取指定话题的历史消息
@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: int
):

    with SessionLocal() as db:

        # 查询指定对话
        conversation = db.get(
            Conversation,
            conversation_id
        )

        if conversation is None:
            raise HTTPException(
                status_code=404,
                detail="聊天话题不存在"
            )

        # 查询该对话的全部消息
        # 按消息 ID 升序排列
        messages = db.scalars(
            select(ChatMessage)
            .where(
                ChatMessage.conversation_id
                == conversation_id
            )
            .order_by(
                ChatMessage.id.asc()
            )
        ).all()

        # 原有的话题序列化函数
        result = serialize_conversation(
            conversation
        )

        # 添加历史消息列表
        result["messages"] = [
            serialize_message(message)
            for message in messages
        ]

        return result
