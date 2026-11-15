"""复用 HippoRAG legacy 的 BM25 配置，只做 MuSiQue 单步检索。

官方来源：OSU-NLP-Group/HippoRAG@b144c46df14cabe5f5822d8caded4bec5f709461
src/elastic_search_tool.py、src/baselines/create_retrieval_index.py、ircot.py
依赖：elasticsearch==8.12.1；服务端按官方 README 使用 8.10.4。
"""

import argparse
import hashlib
import json
from pathlib import Path
from uuid import uuid4


INDEX_BODY = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "index": {"similarity": {"default": {"type": "BM25"}}},
    },
    "mappings": {"properties": {"content": {"type": "text"}}},
}


def evaluate(questions, corpus, rankings):
    """按官方的标题+换行+正文精确匹配，计算逐题宏平均。"""
    passages = [p["title"] + "\n" + p["text"] for p in corpus]
    totals = {f"{metric}@{k}": 0.0 for k in (2, 5, 18)
              for metric in ("R", "All")}
    for question, row in zip(questions, rankings):
        assert question["id"] == row["question_id"]
        gold = {p["title"] + "\n" + p["paragraph_text"]
                for p in question["paragraphs"] if p["is_supporting"]}
        for k in (2, 5, 18):
            retrieved = {passages[i] for i in row["indices"][:k]}
            totals[f"R@{k}"] += len(gold & retrieved) / len(gold)
            totals[f"All@{k}"] += gold <= retrieved
    return {key: value / len(questions) for key, value in totals.items()}


def main():
    from elasticsearch import Elasticsearch

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output-dir", type=Path,
                        default=Path("results/musique/bm25_hipporag_es"))
    parser.add_argument("--es-url", default="http://localhost:9200")
    args = parser.parse_args()

    data_bytes = {name: (args.data_dir / name).read_bytes()
                  for name in ("musique.json", "musique_corpus.json")}
    questions = json.loads(data_bytes["musique.json"])
    corpus = json.loads(data_bytes["musique_corpus.json"])
    args.output_dir.mkdir(parents=True, exist_ok=False)
    index_name = f"musique_{len(corpus)}_bm25_{uuid4().hex[:12]}"

    def save(name, value):
        (args.output_dir / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")

    # 使用独立新索引；保留既有索引和旧实验结果。
    with Elasticsearch(args.es_url, request_timeout=30) as es:
        manifest = {
            "upstream_commit": "b144c46df14cabe5f5822d8caded4bec5f709461",
            "server_version": es.info()["version"],
            "index": index_name,
            "index_body": INDEX_BODY,
            "question_count": len(questions),
            "corpus_count": len(corpus),
            "input_sha256": {name: hashlib.sha256(raw).hexdigest()
                             for name, raw in data_bytes.items()},
            "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        }
        save("manifest.json", manifest)
        es.indices.create(index=index_name, body=INDEX_BODY)
        for i, passage in enumerate(corpus):
            es.index(index=index_name, id=i,
                     body={"content": passage["title"] + "\n" + passage["text"]})
            if (i + 1) % 1000 == 0:
                print(f"Indexed {i + 1}/{len(corpus)}", flush=True)
        es.indices.refresh(index=index_name)
        assert es.count(index=index_name)["count"] == len(corpus)

        rankings = []
        # 与官方单步模式一致：原问题一次检索 Top-100，不调用 LLM。
        for query_index, question in enumerate(questions, 1):
            response = es.search(index=index_name, body={
                "size": 100, "query": {"match": {"content": question["question"]}},
            })
            hits = response["hits"]["hits"]
            rankings.append({"question_id": question["id"],
                             "indices": [int(hit["_id"]) for hit in hits],
                             "scores": [hit["_score"] for hit in hits]})

            if query_index % 100 == 0:
                print(f"Retrieved {query_index}/{len(questions)}", flush=True)

    save("bm25_top100.json", rankings)
    save("bm25_top18.json", [{"question_id": row["question_id"],
                               "indices": row["indices"][:18]} for row in rankings])
    metrics = evaluate(questions, corpus, rankings)
    save("metrics.json", metrics)
    for name, value in metrics.items():
        print(f"{name}: {value * 100:.4f}%")


if __name__ == "__main__":
    main()
