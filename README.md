# TrustData

**正式项目名称：面向众包内容平台的用户评价数据可信评估与分级系统**

TrustData 面向 UGC 平台的数据运营与治理团队，评估一条或一批评价数据在特定下游场景中值得被怎样使用，并保留可复核的证据链。音乐评价平台是首个验证场景。

## 三种使用方式

### 1. 使用本机可视化控制台（推荐）

```powershell
.\.venv\Scripts\python.exe scripts\serve_solution.py
```

访问 `http://127.0.0.1:8000/`。控制台只绑定本机回环地址，提供以下全流程操作：

- 在页面中配置 LLM 提供商、模型、Base URL、抓取参数和 API Key；Key 只保存至本机 `.env`，页面仅显示掩码。
- 选择 CSV、JSON、JSONL 或 Parquet 文件，预览字段并运行 TrustData 数据可信评估。
- 输入自然语言任务或上传 YAML 任务，启动 LLM 跨源挖掘并查看 403/404 来源不可用报告。
- 运行观测数据准备、受控基准、源数据画像、运行清单校验、竞赛包审计与完整测试套件。
- 安装前置研究依赖、运行 AOTY/RYM 八阶段研究，并在明确确认合规后选择实时公开页面采集。
- 在“结果中心”查看实时日志、历史运行和 CSV/JSON/图片/报告产物；每次运行保存在 `outputs/ui-runs/<运行ID>/`，不会默认覆盖正式看板或竞赛证据镜像。

控制台页面右上角的“打开产品看板”保留原静态展示入口。若端口 8000 已被占用，可使用 `--port 8080`；服务仅接受 `127.0.0.1`、`localhost` 或 `::1`。

控制台不会接受跨站写请求：启动页面会建立仅本机可用的短期会话，配置保存、上传和任务启动均需同源 `Origin`、回环 `Host` 与请求 token。请始终从控制台地址打开页面；若页面闲置后提示 token 已过期，刷新页面即可继续。

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

#### 准备环境

请在仓库根目录执行。项目要求 Python 3.12，推荐使用项目虚拟环境，避免系统中其他 Python 或依赖版本影响运行结果。

```powershell
# 首次使用：创建环境并安装全部锁定依赖
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

`requirements.txt` 引用 Python 3.12 的带哈希锁文件；CI 使用更严格的安装方式：

```powershell
.\.venv\Scripts\python.exe -m pip install --require-hashes -r requirements.lock
.\.venv\Scripts\python.exe -m pip check
```

需要更新主项目依赖时，修改 `requirements.in`，使用 Python 3.12 下的 `uv pip compile requirements.in --python-version 3.12 --universal --generate-hashes --output-file requirements.lock` 重新生成锁文件，并运行完整测试。`prior_research/requirements-lock.txt` 是前置研究的独立环境，不应与主项目锁文件混用。

#### 1. 配置 API Key

从模板创建本地配置文件，再用编辑器将占位值替换为真实密钥：

```powershell

Copy-Item .env.example .env
notepad .env
```

默认 `.env` 内容如下：

```dotenv
LLM_API_KEY=your-api-key
```

`scripts/mine_data.py` 每次启动时都会读取仓库根目录的 `.env`。格式为每行一个 `KEY=VALUE`；空行和以 `#` 开头的注释会被忽略。请不要在 `configs/llm_mining.yaml`、命令行参数、日志或提交内容中写入真实密钥。

若同时设置了操作系统环境变量和 `.env` 中的同名变量，**操作系统环境变量优先**。这便于 CI/CD 或团队统一注入密钥，而不会覆盖本机设置。

#### 2. 选择提供商与模型

在 `configs/llm_mining.yaml` 的 `llm` 区块配置提供商、模型和密钥变量名：

| 场景 | `.env` | `configs/llm_mining.yaml` |
| --- | --- | --- |
| OpenAI 或 OpenAI 兼容服务 | `LLM_API_KEY=...` | `api_type: "openai"`、`api_key_env: "LLM_API_KEY"` |
| Anthropic | `ANTHROPIC_API_KEY=...` | `api_type: "anthropic"`、`api_key_env: "ANTHROPIC_API_KEY"` |
| 本地 vLLM、Ollama 或兼容网关 | 按网关要求填写 | 使用 `api_type: "openai"`，并填写 `base_url` |

OpenAI 兼容服务示例：

```yaml
llm:
  api_type: "openai"
  model: "gpt-4o"
  api_key_env: "LLM_API_KEY"
  # 例如：http://localhost:8000/v1
  # base_url: "http://localhost:8000/v1"
  max_tokens: 4096
  temperature: 0.1
```

在同一配置文件的 `crawl` 区块显式登记任务平台可访问的主机名：

```yaml
crawl:
  platform_domains:
    aoty: ["albumoftheyear.org"]
    rym: ["rateyourmusic.com"]
  request_delay: 2.0
  max_pages_total: 50
  max_pages_per_entity: 5
```

`platform_domains` 是必填安全边界：只有任务中平台对应的正式主域或子域可被访问；未知平台、HTTP、IP 地址、私网/回环解析结果以及白名单外的重定向都会被拒绝。`search_hints` 仅提供给模型生成策略，不能扩大可访问域名范围。`max_tokens` 控制单次解析的最大输出长度，`temperature` 建议保持较低值以提高结构化提取稳定性。`crawl` 区块中的 `request_delay`、`max_pages_total` 和 `max_pages_per_entity` 用于约束抓取频率和规模；请遵守目标网站条款、robots 规则与访问频率限制。

#### 3. 运行挖掘任务

可以直接传入自然语言任务：

```powershell
.\.venv\Scripts\python.exe scripts\mine_data.py `
  --task "查找AOTY和RYM上Radiohead OK Computer的评分" `
  --output data\mined\okcomputer.csv
```

也可以使用 YAML 任务文件。任务文件中的 `domain`、`entity_type`、对象、平台和搜索提示都可按领域替换：

```yaml
task:
  domain: "music"
  entity_type: "album"
  entities:
    - name: "OK Computer"
      year: "1997"
  platforms: ["aoty", "rym"]
  search_hints:
    - "https://www.albumoftheyear.org/album/"
  max_pages_per_entity: 3
  language: "en"
```

将上述文件保存为 `tasks/okcomputer.yaml` 后运行：

```powershell
.\.venv\Scripts\python.exe scripts\mine_data.py `
  --task tasks\okcomputer.yaml `
  --output data\mined\okcomputer.csv `
  --verbose
```

`--verbose` 会输出调试日志，适合定位搜索策略、抓取失败或引用验证失败。使用其他配置文件时增加 `--config configs\my_llm_mining.yaml`。

#### 4. 查看输出并进行可信评估

成功后会生成两类文件：

- 指定的结果文件，例如 `data/mined/okcomputer.csv`；包含标准化记录、`source_url`、完整 `content_hash`、`evidence_fingerprint`、字段级 `citation_field_evidence`、`citation_evidence_status`、`verification_level` 与跨源字段。
- 同目录的 `okcomputer.mining_summary.json`；记录任务、页面数量、提取和验证统计等摘要。
- 若全部候选 URL 都返回 `403` 或 `404`，会额外生成 `okcomputer.source_unavailable.json`；其中列出每个尝试 URL、最终状态码和合规的数据获取建议，便于通过授权渠道自行取得数据。

只保留通过引用验证的记录。随后可将结果送入标准可信度评估：

```powershell
.\.venv\Scripts\python.exe scripts\assess_data.py `
  --input data\mined\okcomputer.csv `
  --output data\assessed\okcomputer_scored.csv `
  --scenario ranking_integrity
```

可用场景包括 `ranking_integrity`、`training_data`、`research_dataset` 和 `content_display`，定义见 `configs/trust.yaml`。输入评分应为 0–5 量表；评估输出是数据使用风险建议，不会直接判定用户意图或自动作出处罚。

#### 常见问题

| 现象 | 处理方式 |
| --- | --- |
| `Environment variable 'LLM_API_KEY' is not set` | 确认 `.env` 位于仓库根目录、变量名与 `api_key_env` 一致，并重新运行命令。 |
| 认证失败或 401 | 检查密钥有效性、占位符替换情况，以及 `api_type`、`base_url` 与服务商的匹配关系。 |
| 未提取到记录 | 使用 `--verbose` 检查页面抓取状态、搜索提示与页面正文；被安全策略拦截、缺少两个来源或无法用引文证明实体/评分等字段的记录会被丢弃。 |
| `Task platforms must be explicitly configured` | 在 `crawl.platform_domains` 为任务使用的平台增加正式主机名；不要用 `search_hints` 绕过白名单。 |
| 全部 URL 返回 403/404 | 查看同目录的 `*.source_unavailable.json`，使用其中 URL 通过官方 API、数据导出或平台批准的数据请求自行获取数据；程序不会绕过访问控制。 |
| 输出记录少于预期 | 缩小范围，请勿盲目提高抓取量；检查 `max_pages_total`、`max_pages_per_entity` 及 `min_citation_score`。 |
| 需要无网络测试 | 运行 `python -m pytest -q tests/test_llm_mining.py`；该测试使用模拟请求，不需要 API Key。 |

**反幻觉与证据规则**：每条记录必须附带页面原文引文；系统先验证引文存在，再验证实体、原始评分与量表，以及所有非空的用户、日期和评论字段均由该引文证明。只有字段全部绑定的记录才会输出，并标记为 `verification_level="llm_mined_web_citation_field_bound"`、`citation_confidence=1.0`。单来源实体没有跨源参考分或跨源差距，其跨源覆盖度为零。

### 3. 完整复现实验

```powershell
.\.venv\Scripts\python.exe scripts\prepare_observed_data.py
.\.venv\Scripts\python.exe scripts\run_trustdata.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\verify_run_manifest.py
```

`pytest` 会在已忽略的 `.pytest-tmp/` 下自动生成一套完整受控基准并验证清单、证据镜像和产品指标，因此全新克隆无需预先存在 `outputs/runs/latest`。如需审计某个控制台运行，可显式指定其结果目录：

```powershell
.\.venv\Scripts\python.exe scripts\audit_competition_package.py --run-dir outputs\ui-runs\<运行ID>\results
```

解决方案定位、数据契约、交付与验收标准见 [`docs/solution/`](docs/solution/README.md)。

### 4. GitHub Checks

`.github/workflows/ci.yml` 会在推送到 `master`、面向 `master` 的 Pull Request 以及手动触发时运行：

- Ubuntu 固定使用 CPython 3.12.13；Windows 使用 runner 当前可用的 CPython 3.12 补丁版本，并在日志中输出实际版本；
- 按 `requirements.lock` 的哈希安装依赖，并执行 `pip check`；
- 固定 Python 哈希种子并将 BLAS/OMP 数值线程限制为 1，降低跨平台基准的非确定性；
- 两个平台均运行完整 pytest 套件；
- 无论成功或失败，均尝试上传保留 30 天的 JUnit XML；
- `CI gate` 汇总矩阵结果，适合作为分支保护的必需检查。

每次运行的产物名称包含操作系统和提交 SHA，可在对应 GitHub Actions 运行页下载。首次推送本工作流后，应在仓库分支保护规则中把 `CI gate` 设为 required status check。

## 当前状态

项目已完成数据、算法、产品、内部证明与申报材料闭环。前置研究位于 `prior_research/`，其中的真实归档、合成数据、受控实验和情景模型分别归档；前置结果作为研究基础使用。当前版本加入五个贡献者分组种子敏感性评测、64 项自动化测试和跨交付物证据校验。提交前工作集中于填写团队信息、核对赛事系统字段与准备真实平台试点。

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
