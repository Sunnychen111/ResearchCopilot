import re
import jieba
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

from sqlite_knowledge import load_sqlite_chunks

# 让 jieba 尽量保留科研专业术语
for term in [
    "MPDTrack",
    "SOI",
    "RIA",
    "DPTracker",
    "DFormerV2"
]:
    jieba.add_word(term)

STOP_WORDS = {
    "的", "了", "是", "在", "和", "与",
    "中", "这", "什么", "一个"
}


def tokenize(text: str) -> list[str]:
    """
    对文本进行分词，用于 BM25 检索。

    同时兼容中文提问与英文论文文本。
    """

    text = text.lower()

    # 去除 URL，避免论文链接干扰关键词
    text = re.sub(r"https?://[^\s)]+", " ", text)

    tokens = []

    for word in jieba.lcut(text):

        word = word.strip()

        if not word:
            continue

        if word in STOP_WORDS:
            continue

        # 去除纯标点符号
        if not re.search(
            r"[a-z0-9\u4e00-\u9fff]",
            word
        ):
            continue

        tokens.append(word)

    return tokens


# ==========================================
# 2. SQLite 混合检索器
# ==========================================

class SQLiteHybridRetriever:
    """
    将数据库 Chunk 转换为检索索引。

    包含：
    - BGE 语义检索
    - BM25 关键词检索
    - RRF 排名融合

    当前版本索引保存在内存中。
    """

    def __init__(self):

        print("正在加载 BGE 模型...")

        self.model = SentenceTransformer(
            "BAAI/bge-small-zh-v1.5"
        )

        self.chunks = []
        self.embeddings = None
        self.bm25 = None

        # 初始化时构建一次索引
        self.refresh_index()

    def refresh_index(self):
        """
        从 SQLite 重新加载 Chunk 并构建索引。

        后续 PDF 新增或重新解析后，
        需要主动调用这个函数刷新检索内容。
        """

        print("\n正在读取 SQLite 知识库...")

        self.chunks = load_sqlite_chunks()

        if not self.chunks:

            self.embeddings = None
            self.bm25 = None

            print("数据库中没有可检索的 Chunk")
            return

        # 取出全部 Chunk 正文
        documents = [
            chunk["content"]
            for chunk in self.chunks
        ]

        # 构建 BM25 索引
        tokenized_docs = [
            tokenize(doc)
            for doc in documents
        ]

        self.bm25 = BM25Okapi(tokenized_docs)

        print("BM25 索引构建完成")

        # 批量计算 BGE 向量
        self.embeddings = self.model.encode(
            documents,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=True
        )

        print(
            f"BGE 索引构建完成，"
            f"共 {len(self.chunks)} 个 Chunk"
        )

    # ======================================
    # 3. BGE 语义检索
    # ======================================

    def dense_search(
        self,
        query: str,
        top_k: int = 10
    ) -> list[dict]:

        if self.embeddings is None:
            return []

        # 问题转换为向量
        query_embedding = self.model.encode(
            query,
            normalize_embeddings=True,
            convert_to_numpy=True
        )

        # 归一化后的向量点积 = 余弦相似度
        scores = self.embeddings @ query_embedding

        ranked_indices = sorted(
            range(len(scores)),
            key=lambda i: float(scores[i]),
            reverse=True
        )

        results = []

        for index in ranked_indices[:top_k]:

            chunk = self.chunks[index].copy()

            chunk["score"] = float(scores[index])

            results.append(chunk)

        return results

    # ======================================
    # 4. BM25 关键词检索
    # ======================================

    def sparse_search(
        self,
        query: str,
        top_k: int = 10
    ) -> list[dict]:

        if self.bm25 is None:
            return []

        query_tokens = tokenize(query)

        if not query_tokens:
            return []

        scores = self.bm25.get_scores(query_tokens)

        ranked_indices = sorted(
            range(len(scores)),
            key=lambda i: float(scores[i]),
            reverse=True
        )

        results = []

        for index in ranked_indices[:top_k]:

            score = float(scores[index])

            if score <= 0:
                continue

            chunk = self.chunks[index].copy()

            chunk["score"] = score

            results.append(chunk)

        return results

    # ======================================
    # 5. RRF 混合检索
    # ======================================

    def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        recall_k: int = 10,
        rrf_k: int = 60
    ) -> list[dict]:
        """
        同时执行 BGE 和 BM25 检索。

        RRF 公式：
            1 / (rrf_k + rank)

        最后返回融合排名最高的 top_k 个 Chunk。
        """

        dense_results = self.dense_search(
            query,
            top_k=recall_k
        )

        sparse_results = self.sparse_search(
            query,
            top_k=recall_k
        )

        fused = {}

        for source_name, results in [
            ("BGE", dense_results),
            ("BM25", sparse_results)
        ]:

            for rank, chunk in enumerate(
                results,
                start=1
            ):

                chunk_id = chunk["id"]

                if chunk_id not in fused:

                    fused[chunk_id] = {
                        "id": chunk["id"],
                        "document_id": chunk["document_id"],
                        "filename": chunk["filename"],
                        "page_number": chunk["page_number"],
                        "section": chunk["section"],
                        "content": chunk["content"],
                        "rrf_score": 0.0,
                        "source": []
                    }

                # 累加当前检索通道的排名贡献
                fused[chunk_id]["rrf_score"] += (
                    1.0 / (rrf_k + rank)
                )

                fused[chunk_id]["source"].append(
                    source_name
                )

        # 最终按照 RRF 分数排序
        ranked = sorted(
            fused.values(),
            key=lambda item: item["rrf_score"],
            reverse=True
        )

        return ranked[:top_k]


# ==========================================
# 6. 独立测试
# ==========================================

if __name__ == "__main__":

    retriever = SQLiteHybridRetriever()

    query = (
        "What is recoverable identity ambiguity "
        "in MPDTrack?"
    )

    print("\n用户问题：", query)

    results = retriever.hybrid_search(
        query,
        top_k=5
    )

    print(
        f"\n共检索到 {len(results)} 个结果"
    )

    for rank, chunk in enumerate(
        results,
        start=1
    ):

        print(
            f"\n========== Top {rank} =========="
        )

        print("引用编号：", chunk["id"])
        print("论文名称：", chunk["filename"])
        print("页码：", chunk["page_number"])

        print(
            "RRF 分数：",
            round(chunk["rrf_score"], 5)
        )

        print(
            "检索来源：",
            chunk["source"]
        )

        print(
            "内容预览：",
            chunk["content"][:350]
        )
