import hashlib
import logging
from pathlib import Path

# 设置UUID
from uuid import uuid4

import pymupdf
from fastapi import APIRouter,File,HTTPException,UploadFile
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.database import BASE_DIR,SessionLocal
from backend.model import Document,Chunk
from fastapi import BackgroundTasks
from backend.ingest_pdf import ingest_document
from backend.rag_sqlite import refresh_retrieval
from backend.paper_metadata_db import save_paper_metadata
from threading import Lock

logger = logging.getLogger(__name__)
_parse_lock = Lock()
_recovery_lock = Lock()

# 创建独立路由
router = APIRouter(
    prefix="/api/documents",
    tags=["文献(PDF)管理"]
)

def needs_reparse(db, document: Document) -> bool:
    """
    判断一篇论文是否需要重新解析。

    判断规则：
    1. uploaded / processing / failed：需要恢复
    2. parsed / ready：检查是否存在 Chunk
    3. 正常完成的论文：跳过

    注意：
    作者为空不代表解析失败，例如匿名审稿论文。
    """

    if document.status in {
        "uploaded",
        "processing",
        "failed",
    }:
        return True

    if document.status in {"parsed", "ready"}:

        # 只查询一条 Chunk，避免读取全部正文
        chunk_id = db.scalar(
            select(Chunk.id)
            .where(Chunk.document_id == document.id)
            .limit(1)
        )

        # 声称解析完成，但数据库没有 Chunk
        return chunk_id is None

    return False


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
            "title": document.title,
            "authors": document.authors,
            "venue": document.venue,
            "rank_system": document.rank_system,
            "rank_value": document.rank_value,
            "created_at":(
                document.created_at.isoformat()
                if document.created_at else None
            )
        }
        for document in documents
    ]


def process_document_background(document_id: int) -> bool:
    """
    执行一篇论文的后台解析。

    上传新论文和自动恢复任务统一调用这里。

    返回：
        True：成功重新解析
        False：无需解析或解析失败
    """

    # 任务锁：避免并发解析造成 Chunk 重复删除和写入
    with _parse_lock:

        # 在真正执行之前，再检查一次数据库
        with SessionLocal() as db:

            document = db.get(Document, document_id)

            if document is None:
                logger.warning(
                    "论文不存在：ID=%s",
                    document_id
                )
                return False

            # 例如用户刚上传的论文已经由另一个任务解析完毕
            if not needs_reparse(db, document):
                logger.info(
                    "论文已完成解析，跳过：ID=%s",
                    document_id
                )
                return False

        try:
            logger.info(
                "开始解析或恢复论文：ID=%s",
                document_id
            )

            # 复用现有 PDF -> Chunk 入库流程
            ingest_document(document_id)

            # 如果你之前在这个函数中调用了
            # save_paper_metadata(document_id)，
            # 请在这里保留那一步。
            #
            # 如果元数据已经在 ingest_document()
            # 内部保存，就不必重复调用。

            # 解析完成后刷新 RAG 检索索引
            refresh_retrieval()

            logger.info(
                "论文解析完成：ID=%s",
                document_id
            )

            return True

        except Exception:
            logger.exception(
                "论文解析失败：ID=%s",
                document_id
            )
            return False

def recover_documents_worker(document_ids: list[int]):
    """
    后台逐篇恢复未完成的 PDF。

    单篇失败不会阻止其他文献恢复。
    """

    try:
        total = len(document_ids)
        success = 0

        for index, document_id in enumerate(
            document_ids,
            start=1
        ):

            logger.info(
                "恢复进度 %s/%s，论文 ID=%s",
                index,
                total,
                document_id
            )

            if process_document_background(document_id):
                success += 1

        logger.info(
            "文献自动恢复结束：成功 %s/%s",
            success,
            total
        )

    finally:
        # 无论成功还是失败，都释放批量恢复锁
        _recovery_lock.release()


@router.post("/recover")
def recover_unfinished_documents(
    background_tasks: BackgroundTasks
):
    """
    打开文献库时调用。

    立即检查未完成文献，交给后台恢复，
    不要求浏览器等待实际 PDF 解析结束。
    """

    # 已有恢复任务时，不再创建第二批
    if not _recovery_lock.acquire(blocking=False):
        return {
            "started": False,
            "queued": 0,
            "message": "已有文献恢复任务正在执行"
        }

    try:
        with SessionLocal() as db:

            documents = db.scalars(
                select(Document)
                .order_by(Document.id.asc())
            ).all()

            pending_ids = [
                document.id
                for document in documents
                if needs_reparse(db, document)
            ]

        # 全部正常，无需执行后台任务
        if not pending_ids:
            _recovery_lock.release()

            return {
                "started": False,
                "queued": 0,
                "message": "所有论文均已完成解析"
            }

        # 把耗时任务交给 FastAPI 后台执行
        background_tasks.add_task(
            recover_documents_worker,
            pending_ids
        )

        logger.info(
            "检测到 %s 篇未完成文献：%s",
            len(pending_ids),
            pending_ids
        )

        return {
            "started": True,
            "queued": len(pending_ids),
            "document_ids": pending_ids,
            "message": "已提交后台恢复任务"
        }

    except Exception:
        _recovery_lock.release()
        logger.exception("文献恢复检查失败")
        raise HTTPException(
            status_code=500,
            detail="检查未完成文献失败"
        )
