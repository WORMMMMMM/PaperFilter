#!/usr/bin/env python3
"""
使用 intfloat/e5-large-v2 为论文标题生成语义向量。

输出：
- papers_embeddings.npy : 论文嵌入矩阵 (N, 1024)
- papers_embeddings_meta.json : 每个向量对应的 arXiv ID 与标题
"""

import argparse
import json
import os
from typing import List

import numpy as np
import torch
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


def load_papers(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def build_passage(title: str) -> str:
    title = title.strip()
    return f"passage: {title}" if title else "passage: unknown title"


def generate_embeddings(
    papers: List[dict],
    model_name: str,
    batch_size: int,
    device: str,
):
    sentences = [build_passage(paper.get("title", "")) for paper in papers]
    console_device = device

    print(f"🚀 加载模型 {model_name} (device={console_device}) ...")
    model = SentenceTransformer(model_name, device=device)

    print(f"⚙️  开始编码 {len(sentences)} 篇论文标题（批大小 {batch_size}）...")
    embeddings = model.encode(
        sentences,
        batch_size=batch_size,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    return embeddings


def main():
    parser = argparse.ArgumentParser(description="生成论文标题语义向量")
    parser.add_argument(
        "-i",
        "--input",
        default="papers.json",
        help="输入论文 JSON 文件 (默认: papers.json)",
    )
    parser.add_argument(
        "-e",
        "--embeddings",
        default="papers_embeddings.npy",
        help="输出嵌入文件 (默认: papers_embeddings.npy)",
    )
    parser.add_argument(
        "-m",
        "--metadata",
        default="papers_embeddings_meta.json",
        help="输出元数据文件 (默认: papers_embeddings_meta.json)",
    )
    parser.add_argument(
        "-b",
        "--batch-size",
        type=int,
        default=32,
        help="批大小 (默认: 32)",
    )
    parser.add_argument(
        "--model",
        default="intfloat/e5-large-v2",
        help="SentenceTransformer 模型名 (默认: intfloat/e5-large-v2)",
    )
    parser.add_argument(
        "--device",
        default="cuda" if torch.cuda.is_available() else "cpu",
        help="运行设备 (默认: 自动检测 cuda/cpu)",
    )
    args = parser.parse_args()

    if args.batch_size <= 0:
        parser.error("批大小必须大于 0")

    if not os.path.exists(args.input):
        parser.error(f"找不到输入文件: {args.input}")

    papers = load_papers(args.input)
    if not papers:
        parser.error("输入文件中没有论文数据")

    embeddings = generate_embeddings(
        papers,
        model_name=args.model,
        batch_size=args.batch_size,
        device=args.device,
    )

    os.makedirs(os.path.dirname(args.embeddings) or ".", exist_ok=True)
    np.save(args.embeddings, embeddings)

    metadata = [
        {"arxiv_id": paper.get("arxiv_id"), "title": paper.get("title", "")}
        for paper in papers
    ]
    with open(args.metadata, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    print("✅ 嵌入向量已保存:", args.embeddings)
    print("✅ 元数据已保存:", args.metadata)
    print("🎉 完成！")


if __name__ == "__main__":
    main()

