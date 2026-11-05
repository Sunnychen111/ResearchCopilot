from pathlib import Path

from backend.database import(
    BASE_DIR,
    SessionLocal,
)

from backend.model import Document
from backend.paper_metadata import extract_paper_metadata

def resolve_pdf_path(storage_path:str)->Path:
    path = Path(storage_path)

    if path.is_absolute():
        candidates = [path]

    else:
        candidates = [
            BASE_DIR / path,
            BASE_DIR.parent / path,
        ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()

    raise FileExistsError(
        f"找不到文件：{storage_path}"
    )

def save_paper_metadata(
        document_id: int,
        overwrite: bool = False
)->dict:

    with SessionLocal() as db:
        try:
            document = db.get(
                Document,
                document_id,
            )

            if document is None:
                raise ValueError(
                    f"数据库中不存在论文 ID={document_id}"
                )

            need_title = (
                overwrite or not (document.title or "").strip()
            )

            need_authors = (
                overwrite or not (document.authors or "").strip()
            )

            if not need_title and not need_authors:
                return{
                    "document_id":document_id,
                    "title":document.title,
                    "authors":document.authors,
                    "update":False
                }

            # 根据数据库定位pdf
            pdf_path = resolve_pdf_path(
                document.storage_path
            )

            metadata = extract_paper_metadata(pdf_path)

            new_title = metadata.get("title")
            new_authors = metadata.get("authors")

            changed = False

            if need_title and new_title:
                if document.title != new_title:
                    document.title = new_title
                    changed = True

            if need_authors and new_authors:
                if document.authors!=new_authors:
                    document.authors = new_authors
                    changed =True

            if changed ==True:
                db.commit()
                db.refresh(document)

            return{
                "document_id": document.id,
                "title": document.title,
                "authors": document.authors,
                "updated": changed,
            }
        except Exception:
            db.rollback()
            raise