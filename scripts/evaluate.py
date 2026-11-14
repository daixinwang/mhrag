import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
supporting_path = BASE_DIR / "data" / "musique_supporting_indices.json"
bm25_path = BASE_DIR / "results" / "musique" / "bm25_top18.json"
bge_path = BASE_DIR / "results" / "musique" / "bge_top18.json"
rrf_path = BASE_DIR / "results" / "musique" / "rrf_top18.json"

with open(supporting_path, "r", encoding="utf-8") as f:
    supporting_indices = json.load(f)
with open(bm25_path, "r", encoding="utf-8") as f:
    bm25_results = json.load(f)
with open(bge_path, "r", encoding="utf-8") as f:
    bge_results = json.load(f)
with open(rrf_path, "r", encoding="utf-8") as f:
    rrf_results = json.load(f)

# 标准答案：每道题支持的段落下标
supporting_dict = {item["question_id"]: item["supporting_indices"] for item in supporting_indices}

# 检索结果
def retrieval(results):
    retrieval_dict={}
    for item in results:
        retrieval_dict[item["question_id"]] = item["indices"]

    return retrieval_dict

bm25_dict = retrieval(bm25_results)
bge_dict = retrieval(bge_results)
rrf_dict = retrieval(rrf_results)

# 按跳数分组
groups = {
    "2跳": [],
    "3跳": [],
    "4跳": []
}

for question_id in supporting_dict:
    if question_id.startswith("2hop"):
        groups["2跳"].append(question_id)

    elif question_id.startswith("3hop"):
        groups["3跳"].append(question_id)

    elif question_id.startswith("4hop"):
        groups["4跳"].append(question_id)

print(f"2跳题目数量：{len(groups['2跳'])}")
print(f"3跳题目数量：{len(groups['3跳'])}")
print(f"4跳题目数量：{len(groups['4跳'])}")


# evaluate
def evaluate(retrieval_dict, question_ids):
    recall_2 = []
    recall_5 = []
    recall_18 = []
    all_18 = []

    for question_id in question_ids:
        supporting = set(supporting_dict[question_id])
        retrieved = retrieval_dict[question_id]

        retrieved_2 = set(retrieved[:2])
        retrieved_5 = set(retrieved[:5])
        retrieved_18 = set(retrieved[:18])
        recall_2.append(len(supporting & retrieved_2) / len(supporting))
        recall_5.append(len(supporting & retrieved_5) / len(supporting))
        recall_18.append(len(supporting & retrieved_18) / len(supporting))
        all_18.append(len(supporting & retrieved_18) == len(supporting))

    metrics = {
        "R@2": sum(recall_2) / len(recall_2),
        "R@5": sum(recall_5) / len(recall_5),
        "R@18": sum(recall_18) / len(recall_18),
        "All@18": sum(all_18) / len(all_18)
    }

    return metrics



methods = {
    "BM25": bm25_dict,
    "BGE": bge_dict,
    "RRF": rrf_dict
}

for method_name, retrieval_dict in methods.items():
    print(f"\n{method_name}检索结果评估：")
    # 全部题目
    total = evaluate(retrieval_dict,supporting_dict.keys())
    print("全部题目：")
    for metric, value in total.items():
        print(f"{metric}: {value * 100:.1f}%")

    # 按跳数分别评估
    for group_name, question_ids in groups.items():
        metrics = evaluate(retrieval_dict,question_ids)

        print(f"\n{group_name}（{len(question_ids)}题）：")
        for metric, value in metrics.items():
            print(f"{metric}: {value * 100:.1f}%")
    print()