# TrustData

**正式项目名称：面向众包内容平台的用户评价数据可信评估与分级系统**

TrustData 面向 UGC 平台的数据运营与治理团队，评估一条或一批评价数据在特定下游场景中值得被怎样使用，并保留可复核的证据链。音乐评价平台是首个验证场景。

## 三种使用方式

### 1. 直接查看解决方案

```powershell
.\.venv\Scripts\python.exe scripts\serve_solution.py
```

访问 `http://127.0.0.1:8000/product/`。页面同时包含生成式数据脚本回退，已有 `product/dashboard-data.js` 时也可直接打开 `product/index.html`。

### 2. 评估一批新数据

```powershell
.\.venv\Scripts\python.exe scripts\assess_data.py `
  --input examples\sample_reviews.csv `
  --output outputs\examples\sample_scored.csv `
  --scenario ranking_integrity
```

输入评分需先统一到 0–5 量表。输出提供 DTS、证据覆盖度、不确定性、A–E 等级、风险标签、建议动作和版本信息；结论属于数据使用风险建议，不直接认定用户意图或作出不可逆处罚。

### 2b. 使用 LLM 挖掘跨源验证数据

TrustData 支持使用大模型 API 作为万能爬虫，从多个平台挖掘评价数据用于交叉验证。LLM 驱动搜索策略和页面解析，httpx 负责实际网页抓取，确保数据来自真实 Web 而非模型内部参数。

```powershell
# 安装挖掘依赖
pip install httpx

# 设置 LLM API Key
$env:LLM_API_KEY = "your-api-key"

# 使用自然语言描述挖掘任务
.\.venv\Scripts\python.exe scripts\mine_data.py `
  --task "查找AOTY和RYM上Radiohead OK Computer的评分" `
  --output data\mined\okcomputer.csv

# 使用 YAML 任务文件
.\.venv\Scripts\python.exe scripts\mine_data.py `
  --task tasks\cross_source_movies.yaml `
  --output data\mined\movies.csv `
  --verbose

# 挖掘后用标准流水线评估可信度
.\.venv\Scripts\python.exe scripts\assess_data.py `
  --input data\mined\okcomputer.csv `
  --output data\assessed\okcomputer_scored.csv `
  --scenario ranking_integrity
```

**配置**：编辑 `configs/llm_mining.yaml` 选择 LLM 提供商（OpenAI 兼容 / Anthropic）、设置爬取间隔和验证阈值。支持 `base_url` 覆盖以接入 vLLM、Ollama 或其他兼容端点。

**YAML 任务文件格式**：通过 `domain` 和 `entity_type` 字段切换领域（音乐/电影/餐饮等），详见 `configs/llm_mining.yaml` 中的示例。

**反幻觉与证据规则**：每条提取的记录必须附带 `citation_snippet`（源页面原文子串），系统对引用片段做子串匹配验证，置信度低于阈值的记录自动丢弃。挖掘数据标记为 `verification_level="llm_mined_web_citation"`，进入评估流水线后 P 维度风险自动升高，确保下游使用者知悉数据来源特征。

### 3. 完整复现实验

```powershell
.\.venv\Scripts\python.exe scripts\prepare_observed_data.py
.\.venv\Scripts\python.exe scripts\run_trustdata.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\verify_run_manifest.py
```

解决方案定位、数据契约、交付与验收标准见 [`docs/solution/`](docs/solution/README.md)。

## 当前状态

项目已完成数据、算法、产品、内部证明与申报材料闭环。前置研究位于 `prior_research/`，其中的真实归档、合成数据、受控实验和情景模型分别归档；前置结果作为研究基础使用。当前版本加入五个贡献者分组种子敏感性评测、13 项自动化测试和跨交付物证据校验。提交前工作集中于填写团队信息、核对赛事系统字段与准备真实平台试点。

## 核心闭环

数据接入 → 来源建档 → 行为/内容/跨源/时序信号 → Trust Vector → 场景化 Data Trust Score → 数据分级 → 治理动作 → 审计记录 → 可信数据输出

## 证据规则

- 系统输出记录在指定用途下的风险与使用建议。
- 生成辅助声明作为来源证据，与质量判断分别处理。
- 合成污染统一标记为 E2 受控基准。
- 文本实验用于内容结构特征验证。
- 申报指标均可追溯到本仓库的输入、配置、代码、日志和结果文件。

交付物包括：`deliverables/` 中的申报书 Word/PDF 与路演 PPT，`product/` 中的静态原型，`competition/evidence/` 中的证据索引与运行产物。详见 [PROJECT_SCOPE.md](PROJECT_SCOPE.md)、[CURRENT_STATE.md](CURRENT_STATE.md) 与 [TASK_TREE.md](TASK_TREE.md)。

## 最终验收

```powershell
python scripts/audit_competition_package.py
python scripts/verify_run_manifest.py
pytest -q
```
