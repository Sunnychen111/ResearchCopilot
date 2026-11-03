from sqlalchemy import select

from database import SessionLocal
from model import Chunk

def expand_neighbor_chunks(
        retrieved_docs: list[dict],
        window:int = 2,
        max_chars:int =20000
)->list[dict]:

    if window<0:
        raise ValueError("window 不能小于 0")

    expanded = []
    seen_ids = set()
    total_chars = 0

    def add_chunk(item:dict):
        nonlocal total_chars

        chunk_id = item["id"]

        if chunk_id in seen_ids:
            return

        content_length = len(item['content'])

        if total_chars + content_length >max_chars:
            return 

        expanded.append(item)
        seen_ids.add(chunk_id)
        total_chars+=content_length

    for doc in retrieved_docs:
        add_chunk(doc.copy())

    with SessionLocal() as db:
        for doc in retrieved_docs:

            chunk_id = str(doc["id"])

            if not chunk_id.startswith("C"):
                continue

            try:
                database_id = int(chunk_id[1:])
            except ValueError:
                continue

            target = db.get(Chunk, database_id)

            if target is None:
                continue

            start_index = max(
                0,
                target.chunk_index - window
            )

            end_index = target.chunk_index + window

            # 必须限定 document_id
            # 防止补充到其他论文的 Chunk
            neighbors = db.scalars(
                select(Chunk)
                .where(
                    Chunk.document_id == target.document_id,
                    Chunk.chunk_index >= start_index,
                    Chunk.chunk_index <= end_index
                )
                .order_by(Chunk.chunk_index.asc())
            ).all()

            for neighbor in neighbors:

                neighbor_id = f"C{neighbor.id}"

                if neighbor_id in seen_ids:
                    continue

                # 为新增证据构建与原有 RAG 兼容的结构
                neighbor_doc = {
                    "id": neighbor_id,
                    "document_id": neighbor.document_id,
                    "filename": doc["filename"],
                    "page_number": neighbor.page_number,
                    "section": (
                        f"{doc['filename']} / "
                        f"第 {neighbor.page_number} 页"
                    ),
                    "content": neighbor.content,
                    "rrf_score": 0.0,
                    "source": ["相邻上下文"]
                }

                add_chunk(neighbor_doc)

    print(
        f"原始检索：{len(retrieved_docs)} 个 Chunk"
    )

    print(
        f"扩展完成：{len(expanded)} 个 Chunk"
    )

    print(
        f"总上下文字符数：{total_chars}"
    )

    return expanded
