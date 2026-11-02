import argparse
import re

from sqlalchemy import delete,func,select

from database import BASE_DIR, SessionLocal
from model import Document, Chunk
from pdf_parser import parse_pdf

def ingest_document(document_id: int):
    with SessionLocal() as db:

        document = db.get(Document,document_id)

        if document is None:
            raise ValueError(
                f"未找到论文 ID={document_id}"
            )

        if not document.storage_path:
            raise ValueError("论文没有保存文件路径")

        pdf_path = BASE_DIR / document.storage_path

        print(f"开始处理论文：{document.filename}")
        print(f"文件路径：{pdf_path}")

        document.status = "processing"
        db.commit()

        try:
            parse_chunks = parse_pdf(
                pdf_path,
                chunk_size=800,
                overlap=120
            )

            if not parse_chunks:
                raise ValueError(
                    "PDF 未提取到文本，可能是扫描版 PDF"
                )

            db.execute(
                delete(Chunk).where(
                    Chunk.document_id ==document_id
                )
            )

            chunk_objects = []

            for index,item in enumerate(parse_chunks):
                    chunk = Chunk(
                        document_id=document_id,
                        page_number=item["page_number"],
                        chunk_index=index,
                        content=item["content"]
                    )

                    chunk_objects.append(chunk)

            # 7. 批量添加 Chunk
            db.add_all(chunk_objects)

            document.status = "parsed"
            db.commit()

        except Exception:
            # 撤销本次事务中尚未提交的修改
            db.rollback()

            # 记录解析失败
            document.status = "failed"
            db.commit()

            # 把真实异常继续抛出，方便排查
            raise

        # 查询入库后的Chunk数量
        chunk_count = db.scalar(
             select(func.count(Chunk.id)
            ).where(
                Chunk.document_id == document_id
            )
        ) 
        print(f"\n论文 ID：{document_id}")
        print(f"Chunk 入库数量：{chunk_count}")
        print(f"论文状态：{document.status}")

        # 输出前两个Chunk作为解析的审查
        first_chunks = db.scalars(
            select(Chunk)
            .where(Chunk.document_id == document_id)
            .order_by(Chunk.chunk_index)
            .limit(2)
        ).all()

        for chunk in first_chunks:
            print(
                f"\nChunk {chunk.chunk_index} "
                f"(第 {chunk.page_number} 页)"
            )
            print(chunk.content[:300])

if __name__ == "__main__":

    # 通过命令行传入论文 ID
    parser = argparse.ArgumentParser(
        description="将已上传 PDF 解析并写入 SQLite"
    )

    parser.add_argument(
        "document_id",
        type=int,
        help="documents 表中的论文 ID"
    )

    args = parser.parse_args()

    ingest_document(args.document_id)


  