# check_chunks.py

from sqlalchemy import text
from database import engine

# 当前上传的论文 ID
document_id = 1

with engine.connect() as conn:

    # 查询这篇论文对应的 Chunk 数量
    result = conn.execute(
        text("""
            SELECT COUNT(*)
            FROM chunks
            WHERE document_id = :document_id
        """),
        {"document_id": document_id}
    )

    chunk_count = result.scalar_one()

    print(f"论文 ID：{document_id}")
    print(f"Chunk 数量：{chunk_count}")