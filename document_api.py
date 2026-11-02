import hashlib
import logging
from pathlib import Path

# 设置UUID
from uuid import uuid4

import pymupdf
from fastapi import APIRouter,File,HTTPException,UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from database import BASE_DIR,SessionLocal
from model import Document
from fastapi import BackgroundTasks
from ingest_pdf import ingest_document
from rag_sqlite import refresh_retrieval

logger = logging.getLogger(__name__)

# 创建独立路由
router = APIRouter(
    prefix="/api/documents",
    tags=["文献(PDF)管理"]
)

# PDF 保存目录
Upload_DIR = BASE_DIR / "uploads"
Upload_DIR.mkdir(parents=True,exist_ok=True)

# 单个文件不大于20MB (单位是B)
MAX_PDF_SIZE = 20*1024*1024

@router.post("/upload",status_code=201)
async def upload_document(
    background_tasks:BackgroundTasks,
    file:UploadFile = File(...)
):

    # 只保留文件名，避免实际路径
    filename = (
        (file.filename or "").replace("\\","/").split("/")[-1]
    )

    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="只能上传 PDF 文件"
        )

    # 读取文件
    try:
        content  = await file.read(MAX_PDF_SIZE+1)
    finally:
        await file.close()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="PDF 文件不能为空"
        )

    if len(content)>MAX_PDF_SIZE:
        raise HTTPException(
                    status_code=400,
                    detail="文件不能超过20MB"
                )

    if not content.startswith(b"%PDF-"):
       raise HTTPException(
            status_code=400,
            detail="文件内容不是有效的 PDF"
        )

    # 利用 PyMuPDF 尝试打开 PDF
    try:
        with pymupdf.open(
            stream=content,
            filetype="pdf"
        ) as pdf:
            if pdf.needs_pass:
                raise HTTPException(
                    status_code=400,
                    detail="暂不支持需要密码的 PDF"
                )
            page_count = pdf.page_count

            if page_count ==0:
                raise HTTPException(
                    status_code=400,
                    detail="PDF文件为空"
                )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="PDF 解析失败"
        )

    # 计算文件 SHA256 避免重复上传
    sha256 = hashlib.sha256(content).hexdigest()

    with SessionLocal() as db:

        # 检查文件是否上传
        existing = db.scalar(
            select(Document).where(
                Document.sha256 == sha256
            )
        )

        if existing is not None:
            raise HTTPException(
                status_code=400,
                detail="该文件已上传"
            )

        # 生成唯一的存储名称
        save_name = f"{uuid4().hex}.pdf"
        save_path = Upload_DIR / save_name

        # 数据保存相对路径
        relative_path = f"uploads/{save_name}"

        try:
            # 保存原始 PDF 到磁盘
            save_path.write_bytes(content)

            document = Document(
                filename = filename,
                sha256 = sha256,
                file_size = len(content),
                storage_path = relative_path,
                page_count = page_count,
                status = "uploaded"
            )

            db.add(document)

            # 提交数据库事务
            db.commit()

            db.refresh(document)

            background_tasks.add_task(
                process_document_background,
                document.id
            )
        except IntegrityError:
            db.rollback()

            save_path.unlink(missing_ok = True)

            raise HTTPException(
                status_code=409,
                detail="数据库中已经存在相同文件")
        except Exception:
            db.rollback()
            
            save_path.unlink(missing_ok = True)

            logger.exception("PDF 上传入库失败")
            raise HTTPException(
                status_code=500,
                detail="PDF 保存或数据库载入失败"
            )

        return {
            "id":document.id,
            "filename":document.filename,
            "file_size":document.file_size,
            "page_count":document.page_count,
            "status":document.status,
            "message":"PDF 上传成功"
        }

@router.get("")
def list_documents():
    with SessionLocal() as db:
        documents = db.scalars(
            select(Document).order_by(
                Document.id.desc()
            )
        ).all()

    return[
        {
            "id":document.id,
            "filename":document.filename,
            "file_size":document.file_size,
            "page_count":document.page_count,
            "status":document.status,
            "created_at":(
                document.created_at.isoformat()
                if document.created_at else None
            )
        }
        for document in documents
    ]

def process_document_background(document_id:int):
    try:
        logger.info(
            "开始后台解析论文，ID=%s",
            document_id
        )

        ingest_document(document_id)

        logger.info(
            "论文解析完成"
        )
        refresh_retrieval()

    except Exception:
        logger.exception(
            "后台 PDF 解析失败，ID=%s",
            document_id
        )
