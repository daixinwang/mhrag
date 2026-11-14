import json
import re
from pathlib import Path
from rank_bm25 import BM25Okapi

BASE_DIR = Path(__file__).resolve().parent.parent
questions_path = BASE_DIR / "data" / "musique.json"
corpus_path = BASE_DIR / "data" / "musique_corpus.json"
output_path = BASE_DIR / "results" / "musique"/ "bm25_top18.json"

with open(questions_path, "r", encoding="utf-8") as f:
    questions = json.load(f)

with open(corpus_path, "r", encoding="utf-8") as f:
    corpus = json.load(f)

def tokenize(text):
    转小写，并按照空格和标点进行分词。
    return re.findall(r"\w+", text.lower())


tokenized_corpus=[]
for passage in corpus:
    tokenized_corpus.append(tokenize(passage["title"] + '. ' + passage["text"]))


bm25=BM25Okapi(tokenized_corpus)
print("BM25索引建立完成")
print()

results=[]
for question in questions:
    query=tokenize(question["question"])
    scores=bm25.get_scores(query)
    top_indices=sorted(range(len(scores)),
        key=lambda idx: scores[idx],
        reverse=True
    )[:18]
    
    results.append({
        "question_id": question["id"],
        "indices": top_indices
    })



output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"bm25检索完成")
print(f"完成检索的题目数量：{len(results)}")
if results:
    print(f"每道题检索段落数：{len(results[0]['indices'])}")
    
