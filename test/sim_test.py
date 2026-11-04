
from sentence_transformers import SentenceTransformer, util

model = SentenceTransformer("BAAI/bge-small-zh-v1.5")

sentences = [
    "GPU显存持续增长可能由张量引用未释放导致",
    "为什么深度学习程序运行久了显卡内存越来越大",
    "今天广州天气很好"
]

# 提取文本向量
embeddings = model.encode(
    sentences,
    convert_to_tensor=True
)

# 比较第一句话与后两句话的相似度
sim1 = util.cos_sim(embeddings[0], embeddings[1])
sim2 = util.cos_sim(embeddings[0], embeddings[2])

print("显存问题相似度:", sim1.item())
print("天气问题相似度:", sim2.item())
