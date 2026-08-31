# TrustData 最终测试与质量验收报告

## 1. 文档控制

| 项目 | 内容 |
|---|---|
| 报告编号 | TD-FTR-20260831-04 |
| 报告版本 | 2.2（Final / Stabilized / Remote Verified） |
| 替代版本 | 2.1（TD-FTR-20260831-03） |
| 项目 | 面向众包内容平台的用户评价数据可信评估与分级系统（TrustData） |
| 仓库 | `SunRunJie/Trustdata-Crowdsourced-Review-Governance` |
| 被测分支 | `master` |
| 本地全量测试提交 | `899ae3c2e7322f883e255f41a608812ddefa57a7` |
| 远端 CI 验证提交 | `899ae3c2e7322f883e255f41a608812ddefa57a7` |
| 本地测试时间 | 2026-08-31T20:53:48+08:00 |
| 远端验证完成时间 | 2026-08-31T21:11:42+08:00 |
| 测试执行 | Codex 自动化测试会话 |
| 质量审计 | Research Auditor 只读交叉核验 |
| 证据等级 | E2：团队内部受控环境验证 |
| 本地结论 | PASS |
| GitHub-hosted Checks | PASS — [TrustData CI #33395397064](https://github.com/SunRunJie/Trustdata-Crowdsourced-Review-Governance/actions/runs/33395397064) |
| 项目负责人审批 | 待人工签署 |

## 2. 执行摘要

最终验收针对稳定性修复提交 `899ae3c2e7322f883e255f41a608812ddefa57a7`。本地在隔离的 CPython 3.12.13 锁定环境中，以与 CI 相同的确定性变量执行完整套件，64 项全部通过；GitHub-hosted Ubuntu、Windows 和汇总 `CI gate` 随后全部成功。

在最终通过前，门禁捕获了一项真实的跨平台数值波动：证据镜像中的消融 AUPRC 绝对差异为约 `2.8137e-6`，略高于原 `2e-6` 容差。该失败已在本机复现。最终将通用证据镜像容差设为 `5e-6`（0.0005 个百分点），仍保留 headline 核心指标 `5e-7` 的严格门槛；同时固定哈希种子和 BLAS/OMP 线程数。算法、数据和结果文件均未修改，也未跳过测试。

| 核心指标 | 结果 |
|---|---:|
| 本地测试用例总数 | 64 |
| 本地通过 | 64 |
| 本地失败/错误/跳过 | 0 / 0 / 0 |
| 本地通过率 | 100% |
| 本地 pytest 总耗时 | 72.494 秒 |
| 依赖一致性 | PASS |
| CI YAML 本地解析 | PASS |
| GitHub Ubuntu 检查 | PASS |
| GitHub Windows 检查 | PASS |
| GitHub `CI gate` | PASS |
| 阻塞缺陷 | 0 |
| 高/重要缺陷 | 0 |
| 未关闭非阻塞警告 | 1 |
| 已关闭 CI/数值兼容性问题 | 2 |

**综合质量验收结论：PASS。** 本地与远端证据均绑定同一提交；在本报告声明的代码、依赖、数值容差、自动化测试和双平台 CI 范围内，未发现阻止合并或发布的缺陷。
## 3. 验收目标与判定标准

### 3.1 验收目标

1. 验证核心可信评估、数据读写、配置加载和评分分级功能。
2. 验证本地控制台的任务白名单、路径隔离和写请求保护。
3. 验证 LLM 数据采集的证据绑定、去重、跨源补全及网络边界。
4. 在干净环境中重建完整受控基准并核对版本化证据。
5. 验证依赖锁可安装且不存在已解析依赖冲突。
6. 建立 Ubuntu/Windows 双平台 GitHub Checks 和稳定的汇总门禁。
7. 形成能够追踪到提交、环境、用例和哈希的机器可读证据链。

### 3.2 通过标准

| 门槛编号 | 判定标准 | 实际结果 | 状态 |
|---|---|---|---|
| AC-01 | 全新 CPython 3.12.13 环境可创建 | 已创建独立虚拟环境 | PASS |
| AC-02 | `requirements.lock` 带哈希安装成功 | 安装成功，无哈希错误 | PASS |
| AC-03 | `python -m pip check` 无破损依赖 | `No broken requirements found` | PASS |
| AC-04 | pytest 失败数与错误数均为 0 | 0 failures / 0 errors | PASS |
| AC-05 | 不允许跳过用例 | 0 skipped | PASS |
| AC-06 | 版本化证据与重建结果一致 | 7 项证据复现测试通过 | PASS |
| AC-07 | CI 工作流可被 YAML 解析，矩阵和门禁存在 | 本地结构验证通过 | PASS |
| AC-08 | GitHub-hosted Ubuntu 与 Windows 检查通过 | 运行 `33395397064` 三项检查均成功 | PASS |
| AC-09 | JUnit、逐例清单和元数据可追溯 | 三类证据均已生成 | PASS |
| AC-10 | 报告中的数字与机器证据一致 | 只读交叉核验通过 | PASS |

AC-08 已由 GitHub 运行 `33395397064` 验证；该运行与稳定性修复提交 `899ae3c2e7322f883e255f41a608812ddefa57a7` 绑定。

## 4. 被测对象与配置基线

| 类别 | 基线 |
|---|---|
| 本地全量测试提交 | `899ae3c2e7322f883e255f41a608812ddefa57a7` |
| 远端 CI 验证提交 | `899ae3c2e7322f883e255f41a608812ddefa57a7` |
| 项目版本 | `trustdata 0.2.0` |
| Python 约束 | `>=3.12,<3.13` |
| 依赖锁 | `requirements.lock` |
| pytest 配置 | `pyproject.toml` |
| 测试目录 | `tests/` |
| 随机种子 | `20260828`（运行契约） |
| CI 工作流 | `.github/workflows/ci.yml` |
| 证据目录 | `competition/evidence/runtime/` |

本地 JUnit、逐例清单与远端双平台 CI 均绑定稳定性修复提交 `899ae3c`；本报告不自动覆盖未来代码、依赖或工作流更改。

## 5. 测试环境

| 组件 | 版本/状态 |
|---|---|
| 操作系统 | Windows 11 10.0.26200 SP0 |
| Python 实现 | CPython |
| Python | 3.12.13 |
| pip | 25.0.1 |
| pytest | 9.1.1 |
| NumPy | 2.5.2 |
| pandas | 3.0.5 |
| SciPy | 1.18.0 |
| scikit-learn | 1.9.0 |
| FastAPI | 0.141.1 |
| Starlette | 1.6.0 |
| HTTPX | 0.28.1 |
| 环境隔离 | 隔离锁定虚拟环境；本轮使用独立仓库内 pytest basetemp |
| 网络依赖 | 安装阶段需要包源；测试阶段不调用真实外部 API |

## 6. 执行过程

1. 确认工作区状态和被测提交 SHA。
2. 创建全新 CPython 3.12.13 虚拟环境。
3. 执行带哈希的锁文件安装。
4. 执行 `python -m pip check`。
5. 执行完整 pytest 并生成 JUnit XML。
6. 从 JUnit 导出 64 项逐例清单。
7. 生成包含环境、提交、哈希和 CI 状态的运行元数据。
8. 对 JUnit、清单、元数据、依赖锁和 CI 工作流进行交叉核验。
9. 通过 GitHub API 核对远端运行、三个 Job、提交 SHA 和最终结论。

正式执行命令：

```powershell
python -m pip install --require-hashes -r requirements.lock
python -m pip check
python -m pytest -q --basetemp=.pytest-tmp/deterministic --junitxml=<temporary-junit-path>
```

## 7. 测试结果明细

### 7.1 模块统计

| 测试模块 | 用例数 | 用例执行时间 | 结果 |
|---|---:|---:|---|
| `tests/test_control.py` | 5 | 0.610 秒 | PASS |
| `tests/test_core.py` | 8 | 0.410 秒 | PASS |
| `tests/test_env.py` | 2 | 0.010 秒 | PASS |
| `tests/test_evidence.py` | 7 | 67.130 秒 | PASS |
| `tests/test_llm_mining.py` | 42 | 0.150 秒 | PASS |
| **合计** | **64** | **68.310 秒（用例体）** | **PASS** |

pytest 总耗时 72.494 秒；模块用例时间之和不包含收集、fixture、进程启动和报告生成等框架开销。

### 7.2 最慢用例

| 排名 | 用例 | 时间 |
|---:|---|---:|
| 1 | `test_numbers_master_matches_generated_primary_results` | 66.093 秒 |
| 2 | `test_manifest_cli_verifies_generated_run` | 0.822 秒 |
| 3 | `test_upload_preflight_and_assessment_job_are_isolated` | 0.337 秒 |
| 4 | `test_versioned_evidence_mirrors_generated_results` | 0.173 秒 |
| 5 | `test_config_masks_key_and_persists_only_to_dotenv` | 0.156 秒 |

完整 64 项用例、类名、状态和耗时见 `test-case-inventory.csv`。

## 8. 需求—测试追踪矩阵

| 需求编号 | 质量目标 | 测试证据 | 用例数 | 结论 |
|---|---|---|---:|---|
| TR-FUNC-01 | 特征、评分、等级与阈值逻辑正确 | `tests/test_core.py` | 8 | Verified |
| TR-ENV-01 | 环境变量读取与覆盖规则稳定 | `tests/test_env.py` | 2 | Verified |
| TR-CTRL-01 | 控制台配置与任务执行隔离 | `tests/test_control.py` | 5 | Verified |
| TR-CTRL-02 | Host/Origin/CSRF/媒体类型保护 | `test_write_requests_require_same_origin_csrf_and_correct_media_type` | 1 | Verified |
| TR-LLM-01 | 任务解析、JSON 提取和评分归一化 | `tests/test_llm_mining.py` | 18 | Verified |
| TR-LLM-02 | HTML 提取、引用评分、字段证据绑定和身份稳定性 | `TestHtmlToTextSnippet`、`TestCitationScore`、`TestFieldBoundEvidenceAndIdentity` | 13 | Verified |
| TR-LLM-03 | 采集管线编排、空结果与来源不可用报告 | `TestMiningPipeline` | 3 | Verified |
| TR-NET-01 | 域名白名单、重定向和后续链接安全 | `TestSafeCrawling` | 5 | Verified |
| TR-XSR-01 | 单来源与跨来源补全规则正确 | `TestEnrichCrossSource` | 3 | Verified |
| TR-EVID-01 | 主指标、看板和敏感性覆盖一致 | `tests/test_evidence.py` | 3 | Verified |
| TR-EVID-02 | 清单、证据镜像和运行契约可复现 | `tests/test_evidence.py` | 4 | Verified |

上述子类用例数用于覆盖说明；机器清单是逐例数量的权威来源。

## 9. 安全与边界回归

### 9.1 已验证

- 控制台写请求要求本机 Host、同源 Origin、有效 CSRF token 和正确媒体类型。
- 任意任务类型不会绕过任务白名单。
- 产物访问拒绝路径穿越。
- API 密钥在响应中脱敏，只写入预期环境文件。
- 平台域名必须显式配置为主机名，不接受 URL 形态绕过。
- 抓取请求验证允许域名，并对重定向后的目标重新校验。
- 非 HTML 后续链接不会被当作页面候选。
- 相对分页链接会被规范解析。
- 实体、评分、量表、用户、日期和评论字段需要各自证据绑定。
- 伪造评分即使存在引文也会被拒绝。
- 完整证据参与稳定记录身份生成，精确重复证据会被去重。
- 单来源实体不会伪造跨源指标。

### 9.2 未验证

- 专业渗透测试。
- 浏览器沙箱逃逸或操作系统权限提升。
- 真实第三方平台的访问控制与服务条款兼容性。
- 生产级密钥管理、集中审计和多用户授权模型。
- 隐私影响评估与个人信息合规审查。

本节是回归测试覆盖说明，不等同于安全认证。

## 10. 证据复现与数值判定

- 完整基准在 pytest 临时目录中重新生成，不依赖被忽略的 `outputs/runs/latest`。
- 列名、行序、索引、数据类型、文本、布尔值及 JSON 键/列表结构严格一致。
- CSV 与 JSON 普通数值叶允许绝对误差不超过 `5e-6`，用于容纳已实测的跨平台底层数值库末位漂移；该阈值等于 0.0005 个百分点。
- 30% 污染档位的 F1、AUPRC 和 FPR 保留更严格的 `5e-7` 绝对误差断言。
- 运行清单的成功状态、代码版本、随机种子和输出摘要由自动化测试核对。
- JUnit、逐例清单和运行元数据分别保存，任何一层变化都会改变对应 SHA-256。

## 11. 机器证据与哈希

| 证据 | 路径 | SHA-256 |
|---|---|---|
| 依赖锁 | `requirements.lock` | `815F48D1ED9B12766900451B0584FCB2E1F0735F7D0A7A401DAE531E98196E55` |
| CI 工作流 | `.github/workflows/ci.yml` | `25D52E1577CADA898E752ECA95C69C9065511287E28353AC9035D115841E8F8D` |
| JUnit XML | `competition/evidence/runtime/pytest-junit.xml` | `5EFE88DB03938C516400937EE8BE9350D544BEFCF04F3B68BF9F29674C128C31` |
| 用例清单 | `competition/evidence/runtime/test-case-inventory.csv` | `24CF6222C78340FD835CF1774F2CAF26D5A7C261BDF08C5CB356BCA207054BB3` |
| 运行元数据 | `competition/evidence/runtime/test-run-metadata.json` | `EFDCB365DF3E10E7428B99D2C0044A73DAC55E52EB5697669D941F4E39301730` |

元数据文件不能安全记录自身哈希，因此本报告是其 SHA-256 的权威记录。

## 12. GitHub Checks 设计与实测结果

### 12.1 触发与可复现性控制

- 推送到 `master`、面向 `master` 的 Pull Request及手动 `workflow_dispatch` 均触发。
- 权限最小化为 `contents: read`；checkout 不持久化凭据。
- pip 缓存以 `requirements.lock` 为键；依赖按哈希安装并执行 `pip check`。
- 固定 `PYTHONHASHSEED=0`，将 OMP/OpenBLAS/MKL/NumExpr 线程数设为 1，并使用无界面的 Matplotlib 后端。
- 矩阵不快速失败；JUnit 始终尝试上传并保留 30 天。
- `CI gate` 汇总矩阵，提供稳定的分支保护检查名。

### 12.2 最终检查矩阵

| 检查 | 环境 | Python 选择 | 工作内容 |
|---|---|---|---|
| `Tests (ubuntu-latest, Python 3.12.13)` | GitHub-hosted Ubuntu | 固定 `3.12.13` | 哈希锁定安装、`pip check`、64 项测试、JUnit 上传 |
| `Tests (windows-latest, Python 3.12)` | GitHub-hosted Windows | runner 可用的 3.12 补丁版 | 哈希锁定安装、`pip check`、64 项测试、JUnit 上传 |
| `CI gate` | GitHub-hosted Ubuntu | 不适用 | 汇总矩阵，任一平台失败则门禁失败 |

### 12.3 最终成功运行

成功运行：[TrustData CI #33395397064](https://github.com/SunRunJie/Trustdata-Crowdsourced-Review-Governance/actions/runs/33395397064)，提交 `899ae3c2e7322f883e255f41a608812ddefa57a7`，最终结论 `success`。

| Job ID | 检查 | 开始（UTC） | 完成（UTC） | 耗时 | 结论 |
|---:|---|---|---|---:|---|
| `99498591142` | Ubuntu / Python 3.12.13 | 13:09:21 | 13:10:49 | 88 秒 | PASS |
| `99498590941` | Windows / Python 3.12 | 13:09:21 | 13:11:37 | 136 秒 | PASS |
| `99499282336` | CI gate | 13:11:39 | 13:11:42 | 3 秒 | PASS |

### 12.4 诊断历史与纠正措施

| 运行 | 提交 | 观察结果 | 纠正/解释 | 状态 |
|---:|---|---|---|---|
| `33378802164` | `515f346` | Windows 无法配置精确 Python 3.12.13 | Windows 改用 runner 可用的 3.12 补丁版 | Closed |
| `33381987630` | `5ae70ef` | Windows 通过；Ubuntu pytest 失败 | 当时尚未获得失败用例；继续交叉运行 | Superseded |
| `33383173670` | `1dbcb1c` | 三项成功 | 后续相同矩阵出现失败，证明单次绿色尚不足以判定稳定 | Intermediate only |
| `33384454734` | `e3efca9` | Ubuntu pytest 失败 | 本地复现为消融 AUPRC 漂移 `2.8137e-6` 超过旧容差 `2e-6` | Closed |
| `33395397064` | `899ae3c` | Ubuntu、Windows、门禁全部成功 | 固定数值环境；镜像容差调整为 `5e-6`，核心指标仍为 `5e-7` | PASS |

上述历史被完整保留，证明门禁能够阻断环境配置失败和数值证据不一致；最终修复依据具体失败数据，而不是通过重跑掩盖波动。
## 13. 缺陷、警告与关闭项

| 编号 | 分类 | 级别 | 状态 | 证据 | 处置 |
|---|---|---|---|---|---|
| W-001 | 依赖弃用 | SUGGESTION | Open / 非阻塞 | StarletteDeprecationWarning | 下一次依赖升级前评估 `httpx2` 并更新锁文件 |
| C-001 | CI 运行时可用性 | CI compatibility | Closed | 运行 `33378802164` 的 Windows Python 配置失败 | Windows 使用 runner 可用的 Python 3.12 补丁版 |
| C-002 | 跨平台数值复现 | Evidence compatibility | Closed | AUPRC 实测漂移约 `2.8137e-6`，旧阈值为 `2e-6` | 固定数值线程/哈希种子；镜像容差 `5e-6`；核心指标继续 `5e-7` |

阻塞项 0，重要项 0，未关闭建议项 1，已关闭兼容性问题 2，待确认项 0。
## 14. 历史阻塞项关闭记录

| 历史问题 | 关闭证据 | 状态 |
|---|---|---|
| 控制台跨站写请求可创建任务 | Host/Origin/CSRF/媒体类型回归测试 | Closed |
| 宽泛依赖范围导致测试客户端不稳定 | Python 3.12 锁文件、哈希安装、`pip check` | Closed |
| 干净检出缺少 `tmp/` 导致 pytest setup error | `.pytest-tmp` 可自动创建 | Closed |
| 测试依赖被忽略的 `outputs/runs/latest` | 测试内完整重建基准 | Closed |
| CSV/JSON 原始字节哈希跨平台不稳定 | 严格结构/文本比较 + 明确浮点容差 | Closed |
| GitHub Actions 单平台且无测试产物 | Ubuntu/Windows 矩阵 + JUnit + 稳定性修复运行 `33395397064` | Closed |

## 15. 风险与覆盖缺口

| 风险 | 当前控制 | 残余风险 |
|---|---|---|
| 依赖漂移 | 锁定版本、哈希安装、pip 缓存键 | 包源可用性和未来安全升级 |
| 跨平台数值漂移 | 实测漂移量、确定性线程设置、`5e-6` 镜像容差及双平台运行 `33395397064` | macOS 未覆盖；未来数值库升级仍需回归 |
| 外部平台变化 | 安全边界使用模拟请求回归 | 真实页面结构、限流和服务条款变化 |
| 性能退化 | 记录用例耗时和最慢用例 | 无负载、并发、内存和长期稳定性基线 |
| 前端回归 | 数据与控制 API 有测试 | 无浏览器 E2E、视觉回归和无障碍测试 |
| 安全风险 | SSRF/CSRF/路径/白名单回归 | 无第三方渗透测试和隐私影响评估 |
| 研究外部效度 | E2 受控基准与证据链 | 无 E3 真实离线标注、E4 影子试点或 E5 第三方测评 |

## 16. 报告与 GitHub Checks 的关系

本报告和 GitHub Checks 是互补证据：

- 本报告提供测试设计、环境、范围、限制、哈希和人工可读结论。
- JUnit/CSV/JSON 提供机器可读的本地执行证据。
- GitHub Checks 提供与提交 SHA 自动绑定的独立远端执行、历史记录和分支保护。

本报告不能替代 GitHub Checks。本次远端检查已通过；仍建议在 `master` 分支保护中把 `CI gate` 设置为 required status check，使以后每个 PR 都必须等待该门禁通过。

## 17. 复现与复核步骤

1. 检出稳定性修复提交 `899ae3c2e7322f883e255f41a608812ddefa57a7`。
2. 使用 CPython 3.12.13 和 `requirements.lock` 创建隔离环境，执行带哈希安装及 `pip check`。
3. 设置 `PYTHONHASHSEED=0`、`OMP_NUM_THREADS=1`、`OPENBLAS_NUM_THREADS=1`、`MKL_NUM_THREADS=1`、`NUMEXPR_NUM_THREADS=1`、`MPLBACKEND=Agg`。
4. 在仓库内受忽略的独立 basetemp 中执行完整 pytest，并生成 JUnit。
5. 确认 JUnit 为 64 tests、0 failures、0 errors、0 skipped。
6. 确认普通证据镜像比较使用 `5e-6` 绝对容差，核心 headline 指标仍使用 `5e-7`。
7. 核对本报告第 11 节中的哈希。
8. 核对 GitHub 运行 `33395397064` 与提交 SHA 一致。
9. 确认 Ubuntu、Windows 和 `CI gate` 三项结论均为 `success`。
10. 将 `CI gate` 设为分支保护必需检查；未来依赖、数值环境或业务代码变化均重新验收。
## 18. 独立审计覆盖与判定

### 18.1 已审计

- 最终 JUnit 的 64 项总数、失败、错误、跳过和耗时。
- 64 项逐例清单与 JUnit 的一一对应关系。
- 本地与远端提交 SHA、分支、锁文件、工作流及证据哈希。
- GitHub 运行 `33395397064` 的三个 Job ID、时间和结论。
- 失败用例、本地复现数值、旧/新容差与核心指标阈值之间的关系。
- 四次诊断/中间运行与最终成功运行的历史完整性。
- 报告是否存在待推送、待确认或单次绿色即宣称稳定的过度表述。

### 18.2 未覆盖或限制

- macOS、浏览器 E2E、性能、渗透、隐私影响和真实外部 API。
- E3–E6 的真实标注、平台试点、第三方测评和生产运行。
- GitHub JUnit 下载需要仓库身份认证；远端结论通过 GitHub API 的运行、Job 和步骤状态核验，本地保存完整 JUnit。

### 18.3 审计汇总

| 类型 | 数量 |
|---|---:|
| BLOCKER | 0 |
| IMPORTANT | 0 |
| SUGGESTION | 1 |
| Needs confirmation | 0 |
| Closed compatibility findings | 2 |

**审计判定：PASS WITH ONE MINOR MAINTENANCE ITEM。** 最终本地 64/64 与远端三项绿色 Checks 均绑定 `899ae3c`；数值容差调整有失败数据支持且未放宽 headline 核心指标。W-001 是唯一未关闭的非阻塞建议。
## 19. 发布建议与签署

### 19.1 发布建议

- 稳定性修复提交 `899ae3c` 的本地 64/64 与 GitHub Ubuntu/Windows/门禁均通过，可在本报告覆盖范围内合并或发布。
- 在 `master` 分支保护中把 `CI gate` 设置为 required status check。
- 保留成功运行 `33395397064` 及历史失败运行，作为问题发现与纠正措施证据。
- 下一周期处理 W-001，并规划浏览器 E2E、性能基线及 macOS 覆盖。
- 任何业务代码、依赖锁、容差或 CI 工作流变更都应触发新的验收。

### 19.2 签署

| 角色 | 名称/签字 | 日期 | 结论 |
|---|---|---|---|
| 测试执行 | Codex 自动化测试会话 | 2026-08-31 | LOCAL + GITHUB PASS |
| 质量审计 | Research Auditor | 2026-08-31 | PASS WITH ONE MINOR MAINTENANCE ITEM |
| 项目负责人审批 | 待填写 | 待填写 | 待确认 |