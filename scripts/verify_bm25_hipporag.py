"""离线核对 BM25-ES 数据、排名及指标；不需要 Elasticsearch 或 LLM。"""

import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--result-dir", type=Path,
                        default=Path("results/musique/bm25_hipporag_es"))
    args = parser.parse_args()

    def read_result(name):
        return json.loads((args.result_dir / name).read_text(encoding="utf-8"))

    manifest = read_result("manifest.json")
    inputs = {}
    for name in ("musique.json", "musique_corpus.json"):
        raw = (args.data_dir / name).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == manifest["input_sha256"][name], name
        inputs[name] = json.loads(raw)
    questions = inputs["musique.json"]
    corpus = inputs["musique_corpus.json"]
    assert len(questions) == manifest["question_count"]
    assert len(corpus) == manifest["corpus_count"]

    # 独立转换为文档 ID 集合计分，核对检索脚本的文本集合评分。
    lookup = {p["title"] + "\n" + p["text"]: i for i, p in enumerate(corpus)}
    assert len(lookup) == len(corpus), "duplicate corpus passages"
    rankings = read_result("bm25_top100.json")
    assert len(rankings) == len(questions)
    assert len({q["id"] for q in questions}) == len(questions)
    assert [r["question_id"] for r in rankings] == [q["id"] for q in questions]
    assert read_result("bm25_top18.json") == [
        {"question_id": r["question_id"], "indices": r["indices"][:18]}
        for r in rankings
    ]
    totals = {f"{metric}@{k}": 0.0
              for k in (2, 5, 18) for metric in ("R", "All")}
    for question, row in zip(questions, rankings):
        ids = row["indices"]
        assert len(ids) == len(set(ids)) == len(row["scores"]) == 100
        assert all(type(i) is int and 0 <= i < len(corpus) for i in ids)
        assert all(a >= b for a, b in zip(row["scores"], row["scores"][1:]))
        gold = {lookup[p["title"] + "\n" + p["paragraph_text"]]
                for p in question["paragraphs"] if p["is_supporting"]}
        assert gold, question["id"]
        for k in (2, 5, 18):
            hits = len(gold & set(ids[:k]))
            totals[f"R@{k}"] += hits / len(gold)
            totals[f"All@{k}"] += hits == len(gold)
    metrics = {key: total / len(questions) for key, total in totals.items()}
    recorded = read_result("metrics.json")
    assert recorded.keys() == metrics.keys()
    for key, value in metrics.items():
        assert abs(recorded[key] - value) < 1e-12, key
        print(f"{key}: {value * 100:.4f}%")
    print(f"PASS: {len(questions)} questions, {len(corpus)} passages; "
          "data hashes, Top100/Top18 and all six metrics verified.")


if __name__ == "__main__":
    main()
