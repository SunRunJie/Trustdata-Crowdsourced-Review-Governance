# TrustData Project Scope

## 1. What TrustData does

TrustData 接收平台自有或合法获得的一批评价数据，围绕来源、贡献行为、内容独立性、跨源一致性和时序稳定性产生风险信号；系统将多维证据聚合为 Trust Vector，并按具体使用场景生成 Data Trust Score、证据覆盖率、置信等级、可信分级、建议治理动作和审计记录。

核心问题是：**哪些数据可以进入哪个下游场景、以何种权重进入，以及这一决定基于什么证据。**

## 2. What TrustData does not do

- 不判断一条评论的绝对真假。
- 不承诺识别所有 AI 生成文本。
- 不做通用互联网事实核查或知识问答。
- 不以单个特征（如新账号、短文本、AI disclosure）直接裁决。
- 不把跨平台一致性当作 ground truth。
- 不在 MVP 中训练自有大模型、引入区块链或搭建互联网级微服务。

## 3. Primary users

- UGC 平台数据运营与治理团队；
- 内容完整性/反作弊团队；
- 数据采购、研究数据和 AI 数据质量团队。

## 4. Primary data

标准对象为 `record + contributor + entity + content + timestamp + source + relationship`。MVP 首先支持 CSV、JSON/JSONL 和 Parquet；缺失字段不会被默认为低可信，而会降低 evidence coverage。

## 5. Primary outputs

1. 数据集健康概览；
2. 记录/实体级 Trust Passport；
3. 风险信号与证据列表；
4. A-E 可信分级；
5. 场景化权重与治理建议；
6. Review Queue 与 Audit Trail；
7. 受控污染基准和排序稳健性报告。

## 6. MVP boundary

音乐评价数据是唯一首发验证域。MVP 必须真实运行以下闭环：

`ingest → validate → P/B/C/X/T → coverage/uncertainty → DTS → tier → governance → audit → benchmark → dashboard`

首版数据规模目标不是“爬遍互联网”，而是完整处理全部可合法复用归档，并能在受控基准中扩展到十万级贡献记录。真实数据与受控贡献数据分别存储和展示。

## 7. Future scope

在 schema 和 feature abstraction 稳定后，扩展到影视、图书、游戏、电商和企业反馈；在获得平台授权/API/用户导出后，接入真实贡献级时间面板并校准行为模型。

## 8. Acceptance criteria

- 全部必需阶段 fail-fast，结果清单完整；
- 至少 4 个基线与 1 个多维方案；
- 1/5/10/20/30% 多污染强度；
- Precision、Recall、F1、AUROC、AUPRC、FPR、FNR、Brier、ECE；
- Spearman、Kendall、Top-K overlap、Mean Rank Error、NDCG；
- P/B/C/X/T 消融与权重/阈值/缺失敏感性；
- 新账号等群体的误伤率报告；
- 可演示 Trust Passport、Risk Monitor、Governance Center、Audit Trail；
- 每个申报 claim 有 evidence level、允许表述和禁止表述。

