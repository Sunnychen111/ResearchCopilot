
# repair_document_path.py
# 通过 SHA256 修复已上传论文缺失的保存路径

import hashlib

from sqlalchemy import select

from database import BASE_DIR, SessionLocal
from model import Document


# 保存上传文件的目录
UPLOAD_DIR = BASE_DIR / "uploads"


def repair_paths():

    # 读取 uploads 文件夹中的所有 PDF
    pdf_files = list(UPLOAD_DIR.glob("*.pdf"))

    print(f"本地找到 {len(pdf_files)} 个 PDF 文件")

    # 建立哈希到文件路径的映射
    hash_to_path = {}

    for pdf_path in pdf_files:

        # 计算磁盘中真实文件的 SHA256
        file_hash = hashlib.sha256(
            pdf_path.read_bytes()
        ).hexdigest()

        # 将哈希与文件路径关联
        hash_to_path[file_hash] = pdf_path

    # 查询 SQLite 中所有文献记录
    with SessionLocal() as db:

        documents = db.scalars(
            select(Document)
        ).all()

        for document in documents:

            # 如果已有保存路径，则跳过
            if document.storage_path:
                continue

            # 根据数据库中保存的 SHA256 查找原文件
            pdf_path = hash_to_path.get(document.sha256)

            if pdf_path is None:
                print(
                    f"未找到：ID={document.id}, "
                    f"{document.filename}"
                )
                continue

            # 转换成相对于项目根目录的路径
            relative_path = pdf_path.relative_to(BASE_DIR)

            # 更新 ORM 对象
            document.storage_path = relative_path.as_posix()

            print(
                f"修复成功：ID={document.id}, "
                f"路径={document.storage_path}"
            )

        # 提交数据库事务
        db.commit()

    print("路径检查与修复结束")


if __name__ == "__main__":
    repair_paths()
