# TrustData 最终测试与质量验收报告

## 1. 文档控制

| 项目 | 内容 |
|---|---|
| 报告编号 | TD-FTR-20260831-02 |
| 报告版本 | 2.0（Final） |
| 替代版本 | 1.0（TD-FTR-20260831-01） |
| 项目 | 面向众包内容平台的用户评价数据可信评估与分级系统（TrustData） |
| 仓库 | `SunRunJie/Trustdata-Crowdsourced-Review-Governance` |
| 被测分支 | `master` |
| 被测提交 | `9faf4e8f82a61c0fb4dabcd5c03870921a6508dd` |
| 测试时间 | 2026-08-31T17:13:52.084027+08:00 |
| 测试执行 | Codex 自动化测试会话 |
| 质量审计 | Research Auditor 只读交叉核验 |
| 证据等级 | E2：团队内部受控环境验证 |
| 本地结论 | PASS |
| GitHub-hosted Checks | PENDING — 等待用户推送后执行 |
| 项目负责人审批 | 待人工签署 |

## 2. 执行摘要

本次验收针对包含跨平台 GitHub Actions 门禁的提交 `9faf4e8f82a61c0fb4dabcd5c03870921a6508dd`，在一个全新创建的 CPython 3.12.13 虚拟环境中完成。依赖严格按 `requirements.lock` 的版本和哈希安装，`pip check` 未发现破损依赖，完整 pytest 套件全部通过。

| 核心指标 | 结果 |
|---|---:|
| 测试用例总数 | 64 |
| 通过 | 64 |
| 失败 | 0 |
| 错误 | 0 |
| 跳过 | 0 |
| 通过率 | 100% |
| pytest 总耗时 | 93.234 秒 |
| 依赖一致性 | PASS |
| CI YAML 本地解析 | PASS |
| 阻塞缺陷 | 0 |
| 高/重要缺陷 | 0 |
| 非阻塞警告 | 1 |
| GitHub 远端运行 | 尚未执行 |

**本地质量验收结论：PASS。** 在本报告声明的代码提交、依赖环境和自动化测试范围内，未发现阻止用户推送或进入 GitHub-hosted Checks 的问题。

**远端门禁结论：PENDING。** 本地报告不能声称 GitHub Checks 已通过；推送后必须以 GitHub 上的 `CI gate` 结果作为远端最终状态。

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
| AC-08 | GitHub-hosted Ubuntu 与 Windows 检查通过 | 等待推送 | PENDING |
| AC-09 | JUnit、逐例清单和元数据可追溯 | 三类证据均已生成 | PASS |
| AC-10 | 报告中的数字与机器证据一致 | 只读交叉核验通过 | PASS |

AC-08 是远端状态，不影响“可推送”结论，但在 GitHub 显示绿色 `CI gate` 前，不应表述为“GitHub Checks 已通过”。

## 4. 被测对象与配置基线

| 类别 | 基线 |
|---|---|
| 源代码提交 | `9faf4e8f82a61c0fb4dabcd5c03870921a6508dd` |
| 项目版本 | `trustdata 0.2.0` |
| Python 约束 | `>=3.12,<3.13` |
| 依赖锁 | `requirements.lock` |
| pytest 配置 | `pyproject.toml` |
| 测试目录 | `tests/` |
| 随机种子 | `20260828`（运行契约） |
| CI 工作流 | `.github/workflows/ci.yml` |
| 证据目录 | `competition/evidence/runtime/` |

本报告绑定被测提交，不绑定未来未测试的代码更改。报告提交本身只应包含报告、索引和机器证据，不应夹带业务代码修改。

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
| 环境隔离 | 全新临时虚拟环境 |
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
9. 将 GitHub 远端状态明确标记为待推送验证。

正式执行命令：

```powershell
python -m pip install --require-hashes -r requirements.lock
python -m pip check
python -m pytest -q --junitxml=competition/evidence/runtime/pytest-junit.xml
```

## 7. 测试结果明细

### 7.1 模块统计

| 测试模块 | 用例数 | 用例执行时间 | 结果 |
|---|---:|---:|---|
| `tests/test_control.py` | 5 | 0.639 秒 | PASS |
| `tests/test_core.py` | 8 | 0.403 秒 | PASS |
| `tests/test_env.py` | 2 | 0.044 秒 | PASS |
| `tests/test_evidence.py` | 7 | 74.134 秒 | PASS |
| `tests/test_llm_mining.py` | 42 | 0.196 秒 | PASS |
| **合计** | **64** | **75.416 秒（用例体）** | **PASS** |

pytest 总耗时 93.234 秒；模块用例时间之和不包含收集、fixture、进程启动和报告生成等框架开销。

### 7.2 最慢用例

| 排名 | 用例 | 时间 |
|---:|---|---:|
| 1 | `test_numbers_master_matches_generated_primary_results` | 72.375 秒 |
| 2 | `test_manifest_cli_verifies_generated_run` | 1.519 秒 |
| 3 | `test_upload_preflight_and_assessment_job_are_isolated` | 0.289 秒 |
| 4 | `test_config_masks_key_and_persists_only_to_dotenv` | 0.237 秒 |
| 5 | `test_versioned_evidence_mirrors_generated_results` | 0.191 秒 |

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
- CSV 与 JSON 数值叶允许绝对误差不超过 `2e-6`，用于容纳跨平台底层数值库的末位漂移。
- 30% 污染档位的 F1、AUPRC 和 FPR 保留更严格的 `5e-7` 绝对误差断言。
- 运行清单的成功状态、代码版本、随机种子和输出摘要由自动化测试核对。
- JUnit、逐例清单和运行元数据分别保存，任何一层变化都会改变对应 SHA-256。

## 11. 机器证据与哈希

| 证据 | 路径 | SHA-256 |
|---|---|---|
| 依赖锁 | `requirements.lock` | `815F48D1ED9B12766900451B0584FCB2E1F0735F7D0A7A401DAE531E98196E55` |
| CI 工作流 | `.github/workflows/ci.yml` | `03809696ACC45A01E83448129299B65251AACD3286E103634D3E3C57FF1CDC4C` |
| JUnit XML | `competition/evidence/runtime/pytest-junit.xml` | `C27601E7E38D00099F9BF54E861389BCB44DFFAD8D21839A10E246BE796C7F7D` |
| 用例清单 | `competition/evidence/runtime/test-case-inventory.csv` | `C2A339C293937F8FF1CCB0D3869F77DEF512C1A2D54CECB6378EF8CA46294DBD` |
| 运行元数据 | `competition/evidence/runtime/test-run-metadata.json` | `B96427C5AC2ADA37DC2700D5F8766E5A902E9BFE1FB3759679E8FEA52AE82EB8` |

元数据文件不能安全记录自身哈希，因此本报告是其 SHA-256 的权威记录。

## 12. GitHub Checks 设计

### 12.1 触发条件

- 推送到 `master`。
- 面向 `master` 的 Pull Request。
- 手动 `workflow_dispatch`。

### 12.2 检查矩阵

| 检查 | 环境 | 工作内容 |
|---|---|---|
| `Tests (ubuntu-latest, Python 3.12.13)` | GitHub-hosted Ubuntu | 锁定安装、`pip check`、64 项测试、JUnit 上传 |
| `Tests (windows-latest, Python 3.12.13)` | GitHub-hosted Windows | 锁定安装、`pip check`、64 项测试、JUnit 上传 |
| `CI gate` | GitHub-hosted Ubuntu | 汇总矩阵，任一平台失败则门禁失败 |

其他设计：

- 权限最小化为 `contents: read`。
- checkout 不持久化凭据。
- pip 缓存以 `requirements.lock` 为键。
- 同一 PR/分支的新运行会取消旧运行。
- 矩阵不快速失败，便于同时看到两个平台的诊断。
- JUnit 产物即使测试失败也尝试上传，保留 30 天。
- `CI gate` 提供稳定的分支保护检查名称。

### 12.3 当前状态

本地已完成 YAML 解析、矩阵结构和门禁依赖核验。由于用户要求自行推送，本报告生成时 GitHub-hosted runner 尚未执行这些检查。推送后以 GitHub Actions 页面显示的三项状态为准。

## 13. 缺陷、警告与待确认项

| 编号 | 分类 | 级别 | 状态 | 证据 | 处置 |
|---|---|---|---|---|---|
| W-001 | 依赖弃用 | SUGGESTION | Open / 非阻塞 | StarletteDeprecationWarning | 下一次依赖升级前评估 `httpx2` 并更新锁文件 |
| N-001 | 远端执行 | Needs confirmation | Pending | GitHub-hosted Checks 尚未触发 | 用户推送后确认 `CI gate` 为绿色 |
| N-002 | 工作流平台解析 | Needs confirmation | Pending | 本地 YAML 解析已通过，未使用本机 actionlint | 由 GitHub 首次运行完成最终工作流解释验证 |

阻塞项 0，重要项 0，建议项 1，待确认项 2。

## 14. 历史阻塞项关闭记录

| 历史问题 | 关闭证据 | 状态 |
|---|---|---|
| 控制台跨站写请求可创建任务 | Host/Origin/CSRF/媒体类型回归测试 | Closed |
| 宽泛依赖范围导致测试客户端不稳定 | Python 3.12 锁文件、哈希安装、`pip check` | Closed |
| 干净检出缺少 `tmp/` 导致 pytest setup error | `.pytest-tmp` 可自动创建 | Closed |
| 测试依赖被忽略的 `outputs/runs/latest` | 测试内完整重建基准 | Closed |
| CSV/JSON 原始字节哈希跨平台不稳定 | 严格结构/文本比较 + 明确浮点容差 | Closed |
| GitHub Actions 单平台且无测试产物 | Ubuntu/Windows 矩阵 + JUnit + `CI gate` | Implemented / remote pending |

## 15. 风险与覆盖缺口

| 风险 | 当前控制 | 残余风险 |
|---|---|---|
| 依赖漂移 | 锁定版本、哈希安装、pip 缓存键 | 包源可用性和未来安全升级 |
| 跨平台数值漂移 | Windows 本地通过；CI 增加 Ubuntu/Windows | 远端结果待首次运行，macOS 未覆盖 |
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

本报告不能替代 GitHub Checks。推送后建议在 `master` 分支保护中把 `CI gate` 设置为 required status check；以后每个 PR 都必须等待该门禁通过。

## 17. 复现与复核步骤

1. 检出 `9faf4e8f82a61c0fb4dabcd5c03870921a6508dd`。
2. 使用 CPython 3.12.13 创建全新虚拟环境。
3. 执行 `python -m pip install --require-hashes -r requirements.lock`。
4. 执行 `python -m pip check`。
5. 执行 `python -m pytest -q --junitxml=competition/evidence/runtime/pytest-junit.xml`。
6. 确认 JUnit 为 64 tests、0 failures、0 errors、0 skipped。
7. 核对本报告第 11 节中的哈希。
8. 推送本地提交，等待 Ubuntu、Windows 和 `CI gate`。
9. 在分支保护中将 `CI gate` 设为必需检查。
10. 若远端结果与本报告不同，以远端日志和新生成的 JUnit 为准，并重新评估验收结论。

## 18. 独立审计覆盖与判定

### 18.1 已审计

- JUnit 总数、失败、错误、跳过和耗时。
- 五个测试模块的用例数。
- 被测提交、分支和锁文件哈希。
- JUnit、逐例清单、元数据和 CI 工作流哈希。
- 报告数字与机器证据的一致性。
- “本地通过”与“远端待确认”的状态区分。
- 旧 13 项测试口径是否已清除。
- 证据等级和未覆盖范围是否存在过度表述。

### 18.2 未审计或无法在本地验证

- GitHub-hosted runner 的实际执行结果。
- macOS、浏览器 E2E、性能、渗透、隐私影响和真实外部 API。
- E3–E6 的真实标注、平台试点、第三方测评和生产运行。

### 18.3 审计汇总

| 类型 | 数量 |
|---|---:|
| BLOCKER | 0 |
| IMPORTANT | 0 |
| SUGGESTION | 1 |
| Needs confirmation | 2 |

**审计判定：PASS WITH MINOR ISSUES。** 在已审计范围内未发现阻塞或重要不一致；W-001 为非阻塞维护建议，N-001/N-002 必须在推送后由 GitHub 首次运行确认。

## 19. 发布建议与签署

### 19.1 发布建议

- 当前本地提交可推送到 `origin/master`。
- 推送后不要立即把远端状态写成“通过”，应等待 `CI gate` 变绿。
- 如任一平台失败，保留 Actions JUnit 产物，并以失败平台为准修复。
- 在首次成功运行后启用 `CI gate` 分支保护。
- 下一周期处理 W-001，并规划浏览器 E2E 与性能基线。

### 19.2 签署

| 角色 | 名称/签字 | 日期 | 结论 |
|---|---|---|---|
| 测试执行 | Codex 自动化测试会话 | 2026-08-31 | LOCAL PASS |
| 质量审计 | Research Auditor | 2026-08-31 | PASS WITH MINOR ISSUES |
| 项目负责人审批 | 待填写 | 待填写 | 待确认 |
