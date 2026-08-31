# TrustData 竞赛证据索引

证据包用于校内报名、技术审查和答辩核验。所有性能数字属于 E2 受控合成基准。

| 编号 | 证据 | 路径 | 核验要点 |
|---|---|---|---|
| E01 | 前置研究固定版本 | `prior_research/`、`.gitmodules` | 上游提交 `88e0ab65...`，原研究保持独立版本 |
| E02 | 原始文件画像 | `data/source_catalog.csv`、`data/source_profile.json` | 26 文件、17 CSV、哈希、行列、缺失、重复 |
| E03 | 观测数据摘要 | `data/processed/observed_data_summary.json` | 42,356 实体记录、166,259 评论记录 |
| E04 | 数据接管代码 | `scripts/profile_prior_data.py`、`scripts/prepare_observed_data.py` | 可重复生成 E02/E03 |
| E05 | 算法配置 | `configs/trust.yaml` | 随机种子、规模、权重、阈值策略 |
| E06 | 算法实现 | `src/trustdata/` | 规范化、基准、特征、评分、评估、管线 |
| E07 | 运行清单 | `runtime/run_manifest.json` | 成功状态、环境、输入/输出 SHA-256 |
| E08 | 分类结果 | `results/classification_metrics.csv` | 五档污染 × 六方法 |
| E09 | 排序结果 | `results/ranking_metrics.csv` | Spearman、Kendall、Top-100、MRE、NDCG |
| E10 | 稳健性/消融/公平性 | `results/split_sensitivity_metrics.csv`、`results/split_sensitivity_summary.csv`、`results/ablation_metrics.csv`、`results/fairness_metrics.csv` | 五个贡献者分组种子、P/B/C/X/T 消融、账号年龄清洁 FPR |
| E11 | 图表 | `figures/` | 风险检测、排序、消融、等级分布 |
| E12 | 测试记录 | `TEST_REPORT.md`、`runtime/pytest-junit.xml`、`runtime/test-case-inventory.csv`、`runtime/test-run-metadata.json` | 64/64 本地自动化测试通过；GitHub Ubuntu、Windows 与 CI gate 运行 33383173670 全部通过；逐例状态、提交、环境、哈希、诊断历史和限制可追溯 |
| E13 | 产品原型 | `product/`、`app/data/dashboard.json` | 六工作面；数据由运行管线生成 |
| E14 | 主张映射 | `CLAIM_EVIDENCE.csv` | 每项主张的证据、等级和禁用表述 |
| E15 | 数字母表 | `NUMBERS_MASTER.csv` | 申报和路演数字的唯一引用表 |
| E16 | 方法与限制 | `docs/03_ALGORITHM_AND_METHODS.md`、`docs/04_EVALUATION_AND_LIMITS.md` | 实验设计、失败场景和适用边界 |
| E17 | 外部依据 | `docs/05_LITERATURE_POLICY_LANDSCAPE.md` | 官方政策/标准与论文原文链接 |
| E18 | 最终交付验收 | `competition/FINAL_ACCEPTANCE_REPORT.md`、`scripts/audit_competition_package.py` | 交付完整性、数字、语言与哈希的一键复核 |

## 证据等级

- E0：规划，等待实现或验证。
- E1：功能已实现并可本地运行。
- E2：受控合成基准验证。
- E3：真实离线标注验证。
- E4：真实平台影子试点。
- E5：独立第三方测评。
- E6：规模化生产运行。

本项目当前最高等级为 E2。E3–E6 对应后续真实标注、平台试点、第三方测评和规模化运行。

## 复核顺序

1. 检查 `run_manifest.json` 的状态、种子和输入哈希。
2. 对照 `NUMBERS_MASTER.csv` 与原始结果 CSV。
3. 运行 64 项自动化测试，并核对 JUnit、逐例清单、运行元数据与被测提交 SHA。
4. 运行完整管线并比较输出结构；浮点数允许因底层库差异出现末位差异。
5. 打开本地产品，确认页面数据来自 `dashboard.json`。

## 表述规则

- E2 对应团队内部受控评测；真实平台准确率、客户效果和第三方测评分别需要 E3–E5 证据。
- 风险标签表示受控注入机制，与内容事实判断分别处理。
- RYM 数据保留在内部研究环境，公开材料提供来源与处理说明。
- 团队成员、专利、软著、合同、收入和试点机构均以正式凭证为准。
- 1% 污染下的低 F1 和排序变化纳入完整结果报告。
