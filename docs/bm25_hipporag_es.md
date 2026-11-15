# HippoRAG 配置的 Elasticsearch BM25 实验

本实验于 2026-11-15 完成，使用 MuSiQue 1000 题、11,656 篇候选段落。它为原有 `rank_bm25` 实验补充一组有明确配置来源的词法检索基线，不修改原 BM25、BGE、RRF 的脚本或结果。

## 结果与指标

| 指标 | 原 rank_bm25 | Elasticsearch BM25 |
|---|---:|---:|
| R@2 | 31.0000% | 32.2750% |
| R@5 | 40.3583% | 41.2250% |
| R@18 | 53.8750% | 55.4250% |
| All@2 | 4.0000% | 4.3000% |
| All@5 | 9.7000% | 9.7000% |
| All@18 | 20.6000% | 20.4000% |

R@k 为逐题支持段落召回率的宏平均：每题先计算 Top-k 命中的支持段落数除以全部标注支持段落数，再对所有题取平均。All@k 为 Top-k 找齐全部标注支持段落的题目比例。JSON 指标采用 0–1 的数值，表格显示百分比。

R@2/R@5 按一位小数显示为 **32.3%/41.2%**，与 [HippoRAG（NeurIPS 2024）表 2](https://proceedings.neurips.cc/paper_files/paper/2024/file/6ddc001d07ca4f319af96a3024f6dbd1-Paper-Conference.pdf)及 [GFM-RAG（NeurIPS 2025）表 1](https://proceedings.neurips.cc/paper_files/paper/2025/file/33ca0b1102b54c191a9a45a05adafaf4-Paper-Conference.pdf)的单步 BM25 数值一致。这里复现的是论文报告精度下的汇总指标，没有核对论文原始逐题排名。实现来源为 HippoRAG；GFM-RAG 的公开材料不足以逐项确认其 BM25 底层配置，不能仅凭数值一致认定二者实现完全相同。

这些是检索指标，不是答案 EM/F1。All@5 未提升，All@18 略降，不能把召回提升直接表述为答案质量提升。未进行显著性检验。

## 固定配置

来源为 HippoRAG 第一代 `legacy` 提交 [`b144c46df14cabe5f5822d8caded4bec5f709461`](https://github.com/OSU-NLP-Group/HippoRAG/tree/b144c46df14cabe5f5822d8caded4bec5f709461)：

- [baseline 运行说明](https://github.com/OSU-NLP-Group/HippoRAG/blob/b144c46df14cabe5f5822d8caded4bec5f709461/src/baselines/README.md)
- [索引文本构造](https://github.com/OSU-NLP-Group/HippoRAG/blob/b144c46df14cabe5f5822d8caded4bec5f709461/src/baselines/create_retrieval_index.py)
- [Elasticsearch 索引和查询](https://github.com/OSU-NLP-Group/HippoRAG/blob/b144c46df14cabe5f5822d8caded4bec5f709461/src/elastic_search_tool.py)
- [单步模式和评分](https://github.com/OSU-NLP-Group/HippoRAG/blob/b144c46df14cabe5f5822d8caded4bec5f709461/src/baselines/ircot.py)

| 项目 | 设置 |
|---|---|
| 服务端 / 客户端 | Elasticsearch 8.10.4 / Python `elasticsearch==8.12.1` |
| 本次实际 Lucene | 9.7.0 |
| 文档 | `title + '\n' + text`，单一 `content:text` 字段 |
| Analyzer | 默认 `standard`，不另加停用词过滤或词干化 |
| Similarity | 默认 BM25：`k1=1.2`、`b=0.75`、`discount_overlaps=true` |
| 索引 | 1 个主分片、0 个副本，文档 ID 为语料数组下标 |
| 查询 | 原问题的 `match` 查询，默认 OR，无字段加权或自定义二级排序 |
| 输出 | 单步检索 Top100，然后截取 Top18；不调用 LLM |

默认参数见 [Elasticsearch 8.10 similarity 文档](https://www.elastic.co/guide/en/elasticsearch/reference/8.10/index-modules-similarity.html)。本次同时改变了引擎、分词和文档拼接等设置，未做逐因素消融，不能把差异单独归因于某一个参数。

## 已有结果可以直接复用

产物位于 [`results/musique/bm25_hipporag_es/`](../results/musique/bm25_hipporag_es/)：

| 文件 | 内容 |
|---|---|
| `bm25_top100.json` | 每题 `question_id`、100 个 `indices` 和对应 ES `scores` |
| `bm25_top18.json` | 每题 `question_id`、18 个 `indices`，与原结果格式兼容 |
| `metrics.json` | R@2/5/18、All@2/5/18 |
| `manifest.json` | 官方提交、实际服务器版本、索引设置、输入和运行脚本 SHA256 |

`scripts/bm25_hipporag.py` 保留本次实际运行脚本的原始字节，与 manifest 中的 `script_sha256` 一致。1000 题全部返回 100 个有效且不重复的文档 ID，Top18 是其前缀；使用文档 ID 集合独立评分，与运行脚本的文本集合评分完全一致。

复用前核对数据，尤其不要把整数下标直接套到顺序不同的语料上：

```text
musique.json
98ed4e21d3076532f6388d42320fb809599c63a0d8dffca8ece5e41922be6b46

musique_corpus.json
73157a03ce3f0b1a5673dd5dc12bb970c24976dbffc688af9eecdd758c97ffcb
```

从仓库根目录执行以下命令，无需 ES 或额外 Python 依赖：

```bash
python scripts/verify_bm25_hipporag.py --data-dir data
```

该命令核对输入哈希、题目顺序、排名完整性、Top18 前缀和六项指标。请使用普通 Python 模式，不要使用会禁用断言的 `python -O`。

## 从头复现

所有命令均在仓库根目录运行。数据来自上述固定 HippoRAG 提交；已有相同数据时跳过下载。

```bash
mkdir -p data
curl -fL https://raw.githubusercontent.com/OSU-NLP-Group/HippoRAG/b144c46df14cabe5f5822d8caded4bec5f709461/data/musique.json -o data/musique.json
curl -fL https://raw.githubusercontent.com/OSU-NLP-Group/HippoRAG/b144c46df14cabe5f5822d8caded4bec5f709461/data/musique_corpus.json -o data/musique_corpus.json

python -m venv .venv-bm25-es
. .venv-bm25-es/bin/activate
python -m pip install -r requirements-bm25-es.txt
```

本次已完成的运行使用官方 macOS ARM64 安装包。下面 Docker 命令是相同服务端版本的便捷启动方式，未作为本次运行环境验证；已有兼容的本地 ES 服务时可跳过。

```bash
docker run --name mhrag-bm25-es -d \
  -p 127.0.0.1:9200:9200 \
  -e discovery.type=single-node \
  -e xpack.security.enabled=false \
  -e 'ES_JAVA_OPTS=-Xms1g -Xmx1g' \
  docker.elastic.co/elasticsearch/elasticsearch:8.10.4
```

先用 `curl --fail http://127.0.0.1:9200` 确认服务已就绪且版本为 8.10.4，再执行：

```bash
python scripts/bm25_hipporag.py \
  --data-dir data \
  --output-dir results/musique/bm25_hipporag_es_rerun \
  --es-url http://127.0.0.1:9200

python scripts/verify_bm25_hipporag.py \
  --data-dir data \
  --result-dir results/musique/bm25_hipporag_es_rerun
```

输出目录必须尚不存在；每次运行创建独立的新索引，不覆盖已有实验。如果中途失败，使用新的输出目录重新运行。使用 Docker 示例启动的服务可在实验结束后执行 `docker stop mhrag-bm25-es` 停止；之后可用 `docker start mhrag-bm25-es` 再次启动。

## 如何接入后续实验

1. 数据校验通过后，可直接使用已提供的 ES 排名，后续 Reader 实验无需重跑检索。原 `scripts/evaluate.py` 不会自动读取新目录。
2. `scripts/rrf.py` 会自行构造旧 `BM25Okapi`。仅替换一个结果文件不会改变它的行为；ES+BGE 融合需明确接入新排名并另存结果，本次没有重跑 RRF。
3. 主表答案指标应在同一题集、语料、Reader、提示词及文档/token 预算下补测 EM/F1。不能用这组检索指标替代答案评测。
4. 继续补齐 BGE 配置记录和 Top100，再做 ES+BGE RRF，以及同预算的 RRF 候选经 CE 重排对照。BM25 不是用来替代这些更强的基线。
5. 这批 MuSiQue 题目已用于开发和配置核对，不应称为未曝光的独立泛化确认集。
