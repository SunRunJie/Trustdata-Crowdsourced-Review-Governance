# TrustData 最终测试报告

## 1. 文档控制

| 项目 | 内容 |
|---|---|
| 报告编号 | TD-FTR-20260831-01 |
| 报告版本 | 1.0（Final） |
| 项目 | 面向众包内容平台的用户评价数据可信评估与分级系统（TrustData） |
| 被测分支 | `master` |
| 被测提交 | `43ba8dcc138969548cfa5c79ee25135f41cca22a` |
| 测试日期 | 2026-08-31（Asia/Shanghai） |
| 执行主体 | Codex 自动化测试会话 |
| 证据等级 | E2：团队内部受控环境验证 |
| 报告状态 | 最终版；项目负责人签署栏待人工确认 |

## 2. 执行摘要

本次测试针对 PR #1 合并后的 `master` 提交执行。测试覆盖核心可信评分逻辑、数据读写、环境配置、本地控制台写操作保护、LLM 数据采集安全边界、完整基准重建以及版本化证据一致性。

| 指标 | 结果 |
|---|---:|
| 测试用例总数 | 64 |
| 通过 | 64 |
| 失败 | 0 |
| 错误 | 0 |
| 跳过 | 0 |
| 通过率 | 100% |
| 执行时间 | 76.951 秒 |
| 警告 | 1 个非阻塞弃用警告 |

**验收结论：通过（PASS）。** 在本报告列明的环境、提交和自动化测试范围内，未发现阻塞发布或合并的问题。该结论不扩展为真实平台效度、生产容量或第三方安全认证。

## 3. 测试依据与可追溯性

| 证据 | 值或路径 |
|---|---|
| 源代码版本 | `43ba8dcc138969548cfa5c79ee25135f41cca22a` |
| 依赖锁文件 | `requirements.lock` |
| 锁文件 SHA-256 | `815F48D1ED9B12766900451B0584FCB2E1F0735F7D0A7A401DAE531E98196E55` |
| pytest 配置 | `pyproject.toml` |
| 测试代码 | `tests/` |
| 机器可读报告 | `competition/evidence/runtime/pytest-junit.xml` |
| JUnit SHA-256 | `167A8B9F31740A7F05BBB0EF0384F6CF8F9B8DE379B7B41D94F7727AFC7E4545` |
| 运行清单 | `competition/evidence/runtime/run_manifest.json` |

依赖安装采用带哈希校验的锁文件：

```powershell
python -m pip install --require-hashes -r requirements.lock
```

正式测试命令：

```powershell
python -m pytest -q --junitxml=competition/evidence/runtime/pytest-junit.xml
```

## 4. 测试环境

| 组件 | 版本 |
|---|---|
| 操作系统 | Windows 11 10.0.26200 SP0 |
| Python | CPython 3.12.13 |
| pytest | 9.1.1 |
| NumPy | 2.5.2 |
| pandas | 3.0.5 |
| SciPy | 1.18.0 |
| scikit-learn | 1.9.0 |
| FastAPI | 0.141.1 |
| Starlette | 1.6.0 |
| HTTPX | 0.28.1 |

测试依赖安装在隔离目录中；项目依赖版本与 `requirements.lock` 一致。pytest 临时输出写入被忽略的 `.pytest-tmp/`，不依赖预先存在的目录或版本化运行结果。

## 5. 测试范围与结果

| 测试域 | 文件/分类 | 用例数 | 结果 | 主要核验内容 |
|---|---|---:|---|---|
| 核心功能 | `tests/test_core.py` | 8 | 通过 | 特征范围、缺失处理、重复检测、评分等级、阈值、分组隔离、CSV/JSON 读写 |
| 环境配置 | `tests/test_env.py` | 2 | 通过 | `.env` 解析、覆盖规则、缺失文件处理 |
| 控制台与安全回归 | `tests/test_control.py` | 5 | 通过 | 密钥脱敏、任务白名单、路径保护、Host/Origin/CSRF/媒体类型校验、任务隔离 |
| LLM 数据采集 | `tests/test_llm_mining.py` | 42 | 通过 | 任务解析、JSON 提取、评分归一化、引用评分、字段证据绑定、身份去重、跨源补全、安全抓取与重定向限制 |
| 基准与证据复现 | `tests/test_evidence.py` | 7 | 通过 | 主指标、看板、敏感性覆盖、清单校验、完整基准重建、CSV/JSON 证据镜像、运行契约 |
| **合计** |  | **64** | **通过** |  |

## 6. 证据一致性判定规则

- 列名、行序、索引、数据类型、文本、布尔值及 JSON 键/列表结构严格一致。
- CSV 与 JSON 数值叶允许绝对误差不超过 `2e-6`，用于容纳不同平台数值库产生的末位浮点漂移。
- 30% 污染档位的 F1、AUPRC 和 FPR 等关键主指标继续采用更严格的 `5e-7` 绝对误差断言。
- JSON 运行清单和非数值证据仍进行结构或 SHA-256 校验；不以放宽断言掩盖结构性差异。

## 7. 缺陷、警告与处置

| 编号 | 级别 | 状态 | 说明 | 建议 |
|---|---|---|---|---|
| W-001 | 低 | 非阻塞 | Starlette 提示基于 `httpx` 的 `TestClient` 接口已弃用，建议未来迁移至 `httpx2`。当前 64 项测试均正常通过。 | 在下一次依赖升级前评估 `httpx2` 并更新锁文件。 |

未发现阻塞、高危或导致测试失败的缺陷。

## 8. 限制与未覆盖范围

- 本次正式运行环境为 Windows 11，尚未形成 Linux/macOS 的独立运行证据。
- LLM 与平台抓取测试使用模拟请求，不调用真实 API，也不证明真实平台数据效度。
- 未执行大规模性能、长时间稳定性、内存压力和并发容量测试。
- 未执行浏览器端到端、可访问性、专业渗透测试或隐私影响评估。
- 当前证据等级为 E2，不应表述为第三方测评、真实平台试点或生产认证。

## 9. 与 GitHub Checks 的关系

本报告可作为提交 `43ba8dcc138969548cfa5c79ee25135f41cca22a` 的**临时人工验收证据**，但不能完全替代 GitHub Checks。

| 能力 | 本报告 + JUnit | GitHub Checks |
|---|---|---|
| 证明本次指定提交的本地测试结果 | 可以 | 可以 |
| PR 更新后自动重跑 | 不可以 | 可以 |
| 独立远端执行环境 | 不具备 | 具备 |
| 阻止未通过测试的分支合并 | 不具备 | 可通过分支保护强制执行 |
| 防止报告与代码提交错配 | 依赖人工核对 SHA | 自动绑定提交 SHA |
| 保存日志和历史趋势 | 需人工维护 | 平台自动保存 |

因此，在 GitHub Checks 暂不启用期间，可采用“被测提交 SHA + 本报告 + JUnit XML + 人工签署”作为一次性替代流程；后续 PR 仍建议恢复 GitHub Actions，并将测试任务设为受保护分支的必需检查。

## 10. 复现步骤

1. 检出被测提交：`git checkout 43ba8dcc138969548cfa5c79ee25135f41cca22a`。
2. 使用 CPython 3.12 创建隔离环境。
3. 执行 `python -m pip install --require-hashes -r requirements.lock`。
4. 执行 `python -m pytest -q --junitxml=competition/evidence/runtime/pytest-junit.xml`。
5. 确认结果为 `64 passed, 0 failed, 0 errors, 0 skipped`。
6. 对生成的 JUnit XML 计算 SHA-256，并与本报告记录值核对。

## 11. 签署

| 角色 | 名称/签字 | 日期 | 结论 |
|---|---|---|---|
| 测试执行 | Codex 自动化测试会话 | 2026-08-31 | PASS |
| 项目负责人审批 | 待填写 | 待填写 | 待确认 |
