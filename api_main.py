import logging

from fastapi import FastAPI,HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from openai import OpenAIError

from rag_sqlite import rag_chat
from document_api import router as document_router

from conversation_api import router as conversation_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title = "ReseachCopilot API",
    description= "基于 SQLite、BGE、BM25、RRF "
        "和 DeepSeek 的科研知识库问答系统",
    version="0.2.0"
)

app.include_router(document_router)
app.include_router(conversation_router)

# 允许本地React开发服务器访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"]
)

# 定义检索结果结构

class RetrievedDocument(BaseModel):
    id:str
    section: str
    content: str
    rrf_score: float
    source: list[str]

    document_id : int|None = None
    filename: str |None = None
    page_number: int |None=None

# 定义结果检索结构
class ChatRequest(BaseModel):
    question:str = Field(
        min_length=1,
        max_length=2000,
        description="用户问题"
    )

class ChatResponse(BaseModel):
    question:str
    answer:str
    retrieved_docs:list[RetrievedDocument]

# 检查是否开启健康
@app.get("/health")
def health():
    return{'status':'ok'}

@app.post("/api/chat",
          response_model = ChatResponse)
def chat(request:ChatRequest):
    try:
        result = rag_chat(request.question)
        return {
            "question": request.question,
            "answer": result["answer"] or "",
            "retrieved_docs": result["retrieved_docs"]
        }

    except OpenAIError:
        logger.exception("DeepSeek API调用失败")
        raise HTTPException(
            status_code=502,
            detail="大模型服务暂时不可用"
        )

    except Exception:
        logger.exception("RAG服务内部错误")
        raise HTTPException(
            status_code=500,
            detail="RAG服务内部错误"
        )



