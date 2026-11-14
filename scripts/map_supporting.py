import json
from pathlib import Path

# 获取项目根目录：mhrag/
BASE_DIR = Path(__file__).resolve().parent.parent
# 输入文件
questions_path = BASE_DIR / "data" / "musique.json"
corpus_path = BASE_DIR / "data" / "musique_corpus.json"
# 输出文件
output_path = BASE_DIR / "data" / "musique_supporting_indices.json"

with open(questions_path, "r", encoding="utf-8") as f:
    questions = json.load(f)

with open(corpus_path, "r", encoding="utf-8") as f:
    corpus = json.load(f)

print(f"题目数量：{len(questions)}")
print(f"语料段落数量：{len(corpus)}")
print()

def normalize(text):
    """统一处理文本中的空白字符，减少格式差异造成的匹配失败。"""
    return " ".join(text.split())

corpus_index={}
for idx,passage in enumerate(corpus):
    key=(normalize(passage["title"]), normalize(passage["text"]))
    corpus_index.setdefault(key, []).append(idx)


results=[]
unmatched=[]
total_supporting=0
match_supporting=0

for question in questions:
    supporting_indices = []
    for paragraph in question["paragraphs"]:
        if paragraph["is_supporting"]==True:
            total_supporting+=1
            key=(normalize(paragraph["title"]),normalize(paragraph["paragraph_text"]))
            
            indices=corpus_index.get(key, [])
            if len(indices)==1:
                match_supporting+=1
                supporting_indices.append(indices[0])

            else:
                unmatched.append({
                    "question_id": question["id"],
                    "title": paragraph["title"],
                    "paragraph": paragraph["paragraph_text"],
                    "matched_indices": indices
                })


    results.append({
        "question_id": question["id"],
        "supporting_indices": supporting_indices
    })  #对应语料库段落号



# 保存匹配结果
output_path.parent.mkdir(parents=True,exist_ok=True)

with open(output_path,"w",encoding="utf-8") as f:
    json.dump(results,f,ensure_ascii=False,indent=2)


# 输出检查结果
print(f"题目总数：{len(questions)}")
print(f"支持段落总数：{total_supporting}")
print(f"成功匹配：{match_supporting}")
print(f"未匹配或存在重复匹配：{len(unmatched)}")

if unmatched:
    print("\n未匹配详情：")
    for item in unmatched:
        print(item)

else:
    print("所有支持段落均成功匹配！")