import json
from pathlib import Path
from sentence_transformers import SentenceTransformer
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
questions_path = BASE_DIR / "data" / "musique.json"
corpus_path = BASE_DIR / "data" / "musique_corpus.json"
model_path = BASE_DIR / "models" / "bge-small-en-v1.5"
output_path = BASE_DIR / "results" / "musique"/ "bge_top18.json"

with open(questions_path, "r", encoding="utf-8") as f:
    questions = json.load(f)

with open(corpus_path, "r", encoding="utf-8") as f:
    corpus = json.load(f)

model = SentenceTransformer(model_path)
print("BGE模型加载完成")
print()

corpus_text=[]
for passage in corpus:
    corpus_text.append(passage["title"] + '. ' + passage["text"])

corpus_embeddings = model.encode(
    corpus_text,
    batch_size=8,
    normalize_embeddings=True,
    show_progress_bar=True,
    device="cuda" if model.device.type == "cuda" else "cpu"
)

query_texts=[]
for question in questions:
    query_texts.append("Represent this sentence for searching relevant passages: " + question["question"])

query_embeddings = model.encode(
    query_texts,
    batch_size=8,
    normalize_embeddings=True, # 归一化
    show_progress_bar=True,  # 进度条
    device="cuda" if model.device.type == "cuda" else "cpu"
)


results=[]
for i,question in enumerate(questions):
    scores=np.dot(corpus_embeddings, query_embeddings[i])
    top_indices=np.argsort(scores)[::-1][:18]
    
    results.append({
        "question_id": question["id"],
        "indices": top_indices.tolist()
    })


output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print("BGE检索完成")
print(f"完成检索的题目数量：{len(results)}")
if results:
    print(f"每道题检索段落数：{len(results[0]['indices'])}")

