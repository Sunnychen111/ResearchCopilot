from fastapi import APIRouter
from pydantic import BaseModel,Field
from sqlalchemy import select,func,inspect

from database import SessionLocal
from model import Conversation,ChatMessage


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