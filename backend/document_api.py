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
from backend.rag_sqlite import refresh_retrieval,get_retriever
from backend.paper_metadata_db import save_paper_metadata
from threading import Lock
from pydantic import BaseModel,Field

logger = logging.getLogger(__name__)
_parse_lock = Lock()
_recovery_lock = Lock()

# 创建独立路由
router = APIRouter(
    prefix="/api/documents",
    tags=["文献(PDF)管理"]
)

class PublicationUpdate(BaseModel):
    venue: str|None =Field(
        default = None,
        max_length = 255
    )

    rank_system:str |None = Field(
        default = None,
        max_length = 50
    )

    rank_value:str |None =Field(
        default=None,
        max_length = 50
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

def empty_to_none(value:str|None)->str|None:
    if value is None:
        return None
    
    return value.strip() or None




@router.patch("/{document_id}/publication")
def update_publication(
    document_id: int,
    payload: PublicationUpdate
):
    """
    更新论文发表来源和分级。

    只修改：
    venue
    rank_system
    rank_value

    不修改 PDF、Chunk 和标题作者。
    """

    # 1. 获取用户实际提交的字段
    changes = {
        name: empty_to_none(value)
        for name, value in payload.model_dump(
            exclude_unset=True
        ).items()
    }

    # 2. 避免与解析任务同时修改数据库记录
    with _parse_lock:

        # 3. 打开数据库会话
        # 后续查询、修改和 commit 都必须在这里面
        with SessionLocal() as db:

            document = db.get(
                Document,
                document_id
            )

            if document is None:
                raise HTTPException(
                    status_code=404,
                    detail="论文不存在"
                )

            # 4. 计算本次更新后的字段值
            # 没有提交的字段保留原值
            new_venue = changes.get(
                "venue",
                document.venue
            )

            new_system = changes.get(
                "rank_system",
                document.rank_system
            )

            new_value = changes.get(
                "rank_value",
                document.rank_value
            )

            # 5. 定义合法评价体系
            valid_grades = {
                "CCF": {"A", "B", "C"},
                "CAS": {"1区", "2区", "3区", "4区"},
            }

            # 6. 校验评价体系与等级
            if new_system is None:

                # 未选择评价体系时不能填写等级
                if new_value is not None:
                    raise HTTPException(
                        status_code=422,
                        detail="未选择评价体系，不能填写等级"
                    )

            elif new_system not in valid_grades:

                raise HTTPException(
                    status_code=422,
                    detail="评价体系仅支持 CCF 或 CAS"
                )

            elif (
                new_value is not None
                and new_value not in valid_grades[new_system]
            ):

                raise HTTPException(
                    status_code=422,
                    detail="评价等级与评价体系不匹配"
                )

            # 7. 修改 ORM 对象
            # 注意：这里已经退出了上面的 if / elif
            # 但仍然位于数据库 Session 内部
            document.venue = new_venue
            document.rank_system = new_system
            document.rank_value = new_value

            # 8. 提交到 SQLite
            try:
                db.commit()
                db.refresh(document)

            except Exception:
                db.rollback()

                logger.exception(
                    "论文发表信息保存失败：ID=%s",
                    document_id
                )

                raise HTTPException(
                    status_code=500,
                    detail="论文发表信息保存失败"
                )

            # 9. 返回实际写入的内容
            return {
                "message": "论文发表信息修改成功",
                "id": document.id,
                "venue": document.venue,
                "rank_system": document.rank_system,
                "rank_value": document.rank_value,
            }

def find_managed_pdf(storage_path: str) -> Path | None:
    """
    查找 ResearchCopilot 管理的 PDF 副本。

    只允许访问项目 uploads 目录中的 PDF，
    避免误删用户电脑上的其他文件。

    兼容：
    backend/uploads/xxx.pdf
    uploads/xxx.pdf
    """

    stored = Path(storage_path)

    # 只接受 uploads/文件名.pdf 格式
    if (
        stored.is_absolute()
        or len(stored.parts) != 2
        or stored.parts[0] != "uploads"
        or stored.suffix.lower() != ".pdf"
    ):
        raise HTTPException(
            status_code=409,
            detail="PDF 存储路径不符合受管目录规则，已拒绝删除"
        )

    # 兼容项目重构前后的两个上传目录
    upload_dirs = [
        BASE_DIR / "uploads",
        BASE_DIR.parent / "uploads",
    ]

    for upload_dir in upload_dirs:

        root = upload_dir.resolve()
        candidate = (upload_dir / stored.name).resolve()

        # 防止路径跳出 uploads 文件夹
        if candidate.parent != root:
            raise HTTPException(
                status_code=409,
                detail="检测到不安全的 PDF 存储路径"
            )

        if candidate.is_file():
            return candidate

    # 文件可能之前已经丢失
    # 返回 None，不影响数据库记录删除
    return None


@router.delete("/{document_id}")
def delete_document(document_id: int):
    """
    删除指定论文。

    处理内容：
    1. documents 中的论文记录
    2. chunks 中的相关文本
    3. uploads 中的 PDF 副本
    4. RAG 内存检索缓存

    注意：该操作不可通过 API 撤销。
    """

    # 与 PDF 解析任务共用锁，
    # 防止删除过程中后台仍在处理同一篇论文
    with _parse_lock:

        with SessionLocal() as db:

            # 1. 查询指定论文
            document = db.get(
                Document,
                document_id
            )

            if document is None:
                raise HTTPException(
                    status_code=404,
                    detail="论文不存在"
                )

            # 2. 获取需要删除的 PDF 文件
            pdf_path = find_managed_pdf(
                document.storage_path
            )

            filename = document.filename

            # 3. 删除数据库中的论文
            try:

                # 因为 Chunk 与 Document 存在级联关系，
                # 对应的 Chunk 也会被清理
                db.delete(document)

                # 真正提交到 SQLite
                db.commit()

            except Exception:

                db.rollback()

                logger.exception(
                    "删除论文数据库记录失败：ID=%s",
                    document_id
                )

                raise HTTPException(
                    status_code=500,
                    detail="删除论文数据库记录失败"
                )

        # 4. 清除 RAG 缓存
        # 下一次调用 get_retriever() 时，
        # 会从最新数据库重新建立检索索引。
        get_retriever.cache_clear()

        # 5. 删除 PDF 文件副本
        file_deleted = False
        file_warning = None

        if pdf_path is not None:

            try:
                pdf_path.unlink()
                file_deleted = True

            except OSError:

                logger.exception(
                    "PDF 文件删除失败：%s",
                    pdf_path
                )

                file_warning = (
                    "数据库已删除，但 PDF 文件移除失败，"
                    "需要手动清理"
                )

        else:
            file_warning = (
                "数据库已删除，原 PDF 文件不存在"
            )

        # 6. 返回删除结果
        return {
            "message": "文献数据库记录删除成功",
            "deleted_id": document_id,
            "filename": filename,
            "file_deleted": file_deleted,
            "warning": file_warning,
        }
