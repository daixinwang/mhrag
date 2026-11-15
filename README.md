# MuSiQue retrieval experiments

MuSiQue 上的 BM25、BGE 和 RRF 检索实验。

- 原始脚本：`scripts/bm25.py`、`scripts/bge.py`、`scripts/rrf.py`。
- 原始结果：`results/musique/*_top18.json`。
- 新增 [HippoRAG 配置的 Elasticsearch BM25 实验](docs/bm25_hipporag_es.md)：提供可运行脚本、1000 题 Top100/Top18 排名、配置记录和离线评分检查。R@2 为 **32.2750%**，R@5 为 **41.2250%**。

原始 `scripts/evaluate.py` 仍读取原来的三组结果。新 ES 结果单独存放，使用 `scripts/verify_bm25_hipporag.py` 核对，具体命令见实验说明。
