from sqlalchemy import select,func

from database import SessionLocal
from model import Document,Chunk

def list_document_status() ->list[dict]:
    with SessionLocal() as db:

        stmt = (
            select(
                Document.id,
                Document.filename,
                Document.status,
                func.count(Chunk.id).label("chunk_count")
            ).outerjoin(
                Chunk,
                Chunk.document_id ==Document.id
            )
            .group_by(
                Document.id,
                Document.filename,
                Document.status
            ).order_by(Document.id)
        )

        rows = db.execute(stmt).all()

        return [
            {
                "id":row.id,
                "filename":row.filename,
                "status":row.status,
                "chunk_count":row.chunk_count
            }
            for row in rows
        ]

def load_sqlite_chunks() ->list[dict]:
    with SessionLocal() as db:

        stmt=(
            select(
                Chunk.id,
                Chunk.document_id,
                Chunk.page_number,
                Chunk.chunk_index,
                Chunk.content,
                Document.filename
            )
            .join(
                Document,
                Chunk.document_id == Document.id
            )
            .where(Document.status == "parsed")
            .order_by(
                Chunk.document_id,
                Chunk.chunk_index
            )
        )

        rows = db.execute(stmt).all()

        chunks = []

        for row in rows:
            chunk_id = f"C{row.id}"

            chunks.append({
                "id":chunk_id,
                "document_id":row.document_id,
                "filename":row.filename,
                "page_number":row.page_number,
                "section": (
                    f"{row.filename} / "
                    f"第 {row.page_number} 页"
                ),

                # 真正用于 BGE 和 BM25 的文本
                "content": row.content
            })

        return chunks

if __name__ == "__main__":

    print("========== SQLite 论文统计 ==========")

    # 检查数据库中有哪些文献
    documents = list_document_status()

    for doc in documents:
        print(
            f"论文 ID：{doc['id']} | "
            f"文件：{doc['filename']} | "
            f"状态：{doc['status']} | "
            f"Chunk 数量：{doc['chunk_count']}"
        )

    print("\n========== 读取可检索 Chunk ==========")

    chunks = load_sqlite_chunks()

    print(f"可检索 Chunk 总数：{len(chunks)}")

    if not chunks:
        print(
            "当前没有已解析的 Chunk。"
            "请先执行 PDF 入库。"
        )

    else:
        # 只打印前 3 个 Chunk，避免输出过多
        for chunk in chunks[:3]:

            print("\n--------------------")

            print("Chunk ID：", chunk["id"])
            print("论文名称：", chunk["filename"])
            print("页码：", chunk["page_number"])
            print("内容预览：")
            print(chunk["content"][:200])

        # 检查每个 Chunk 是否存在必要信息
        assert all(
            chunk["id"]
            and chunk["filename"]
            and chunk["content"].strip()
            and chunk["page_number"] >= 1
            for chunk in chunks
        )

        # 确认每个 Chunk 的引用 ID 唯一
        chunk_ids = [chunk["id"] for chunk in chunks]

        assert len(chunk_ids) == len(set(chunk_ids))

        print("\nSQLite Chunk 读取验证通过！")
