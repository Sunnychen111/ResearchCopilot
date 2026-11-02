
import sqlite3
from database import DB_PATH

# 连接当前项目使用的 SQLite 数据库
conn = sqlite3.connect(DB_PATH)

# 查询每篇论文对应的 Chunk 数量
sql = """
SELECT
    d.id,
    d.filename,
    d.status,
    COUNT(c.id) AS chunk_count
FROM documents d
LEFT JOIN chunks c
    ON d.id = c.document_id
GROUP BY d.id, d.filename, d.status
ORDER BY d.id;
"""

rows = conn.execute(sql).fetchall()

print("数据库位置：", DB_PATH)
print("\n========== 文献入库检查 ==========")

for row in rows:
    print(
        f"ID: {row[0]} | "
        f"论文: {row[1]} | "
        f"状态: {row[2]} | "
        f"Chunk 数量: {row[3]}"
    )

print("\n文献总数：", len(rows))
print(
    "Chunk 总数：",
    sum(row[3] for row in rows)
)

conn.close()
