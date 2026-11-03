from rag_context import expand_neighbor_chunks

# 模拟检索命中 C314
retrieved_docs = [{
    "id": "C314",
    "document_id": 0,
    "filename": "DUTrack.pdf",
    "page_number": 6,
    "section": "Experiments",
    "content": "DUTrack-256 achieves comparable results...",
    "rrf_score": 0.03,
    "source": ["BGE", "BM25"]
}]

expanded = expand_neighbor_chunks(
    retrieved_docs,
    window=2
)

for doc in expanded:
    print(f"\n========== {doc['id']} ==========")
    print("页码：", doc["page_number"])
    print("来源：", doc["source"])
    print(doc["content"])