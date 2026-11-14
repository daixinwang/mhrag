import json
import re
from pathlib import Path
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
questions_path = BASE_DIR / "data" / "musique.json"
corpus_path = BASE_DIR / "data" / "musique_corpus.json"
model_path = BASE_DIR / "models" / "bge-small-en-v1.5"
output_path = BASE_DIR / "results" / "musique"/ "rrf_top18.json"

with open(questions_path, "r", encoding="utf-8") as f:
    questions = json.load(f)

with open(corpus_path, "r", encoding="utf-8") as f:
    corpus = json.load(f)

# bm25检索
def tokenize(text):
    '''转小写，并按照空格和标点进行分词。'''
    return re.findall(r"\w+", text.lower())

corpus_text=[]
for passage in corpus:
    corpus_text.append(passage["title"] + '. ' + passage["text"])

tokenized_corpus=[]
for text in corpus_text:
    tokenized_corpus.append(tokenize(text))

bm25=BM25Okapi(tokenized_corpus)
print("BM25索引建立完成")
print()


# BGE模型检索
model = SentenceTransformer(model_path)
print("BGE模型加载完成")
print()

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


# RRF融合检索
results=[]
k = 60

for i, question in enumerate(questions):
    #bm25
    query=tokenize(question["question"])
    scores1=bm25.get_scores(query)
    bm25_order=np.argsort(-scores1)
    bm25_ranks=np.argsort(bm25_order)

    # BGE
    scores2=np.dot(corpus_embeddings,query_embeddings[i])
    bge_order = np.argsort(-scores2)
    bge_ranks = np.argsort(bge_order)

    # RRF
    rrf_scores=(1/(k+bm25_ranks+1)+1/(k+bge_ranks+1))
    top_indices=np.argsort(-rrf_scores)[:18]

    results.append({
        "question_id": question["id"],
        "indices": top_indices.tolist()
    })


output_path.parent.mkdir(parents=True, exist_ok=True)
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

print(f"rrf检索完成")
print(f"完成检索的题目数量：{len(results)}")
if results:
    print(f"每道题检索段落数：{len(results[0]['indices'])}")