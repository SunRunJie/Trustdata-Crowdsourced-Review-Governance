# TrustData 最终测试与质量验收报告

## 0. PR #2 交付物一致性增量验收

| 项目 | 内容 |
|---|---|
| 增量报告编号 | TD-FTR-20260901-06 |
| 增量报告版本 | 4.0（PR #2 / Deliverable Consistency / Maintainer Corrected） |
| 被测对象 | Pull Request #2：fix-material-consistency |
| PR 原始提交 | e53bd5a418280c9881038a8e0e9560957f0430f7 |
| 合并基线 | d021a8c2ab81c6365f6e173c2287159b0a2dc280（master） |
| 本地验收时间 | 2026-09-01T20:45:23+08:00 |
| 验收范围 | DOCX、PDF、PPTX、源文案、数值一致性及完整回归 |
| 本地技术验收 | **PASS** |
| GitHub-hosted Checks | **PASS — [TrustData CI #33511108745](https://github.com/SunRunJie/Trustdata-Crowdsourced-Review-Governance/actions/runs/33511108745)** |
| 合并判定 | **PASS — 已合并** |

本次增量验收覆盖 PR #2 的三份展示材料，以及维护者在合并前完成的指标、图表、表格、讲者备注和模板主题修复。正式主指标统一为：30% 污染 F1 0.7492478、AUPRC 0.9489835、FPR 0.0017301；五次贡献者分组复算的 F1 中位数 0.7515026，范围 0.7442975–0.7643808；排序平均名次误差由 20.3960 降至 15.2335，降幅 25.31%。

| 验收项 | 结果 | 状态 |
|---|---|---|
| 锁定依赖一致性 | pip check 无破损依赖 | PASS |
| 全量自动化测试 | 67 项全部通过；0 失败、0 错误、0 跳过；1 条第三方弃用警告 | PASS |
| 竞赛材料包审计 | 使用本轮测试新生成结果执行，27/27 检查通过 | PASS |
| DOCX / PDF 视觉检查 | 7 页逐页检查；无截断、遮挡、异常换页或表格溢出 | PASS |
| PDF 结构检查 | 7 页、未加密、可提取文本 5,439 字符 | PASS |
| PPTX 视觉检查 | 12 页逐页检查；图表、标题、备注与关键数值一致 | PASS |
| PPTX 越界检查 | 官方 slides_test.py 返回 No overflow detected | PASS |
| OOXML 完整性 | DOCX、PPTX 全部压缩条目可读 | PASS |
| PPTX 模板保持 | 三个有效主题部件与原模板主题 SHA-256 字节一致 | PASS |
| PPTX 占位符检查 | 未发现空占位符 | PASS |
| 指标一致性 | DOCX、PDF、PPTX 及源文案包含新指标；活动材料未残留旧指标 | PASS |
| 主题恢复复验 | 恢复原模板主题后 12 张渲染图与恢复前逐字节一致 | PASS |

PR #2 没有可复用的预合并 GitHub Check Runs。本地结论未被用来冒充远端检查。合并提交 fb2cb17e711b4f1d13436c86d5784fe4f9539283 推送后，GitHub Actions 运行 #33511108745 独立执行 Ubuntu、Windows、macOS 与 CI gate；四项均以 success 完成，远端技术验收为 PASS。

本节是当前 PR #2 的增量验收结论。后续第 1–12 节保留 PR #3 的跨平台可复现性基线、远端检查证据和完整方法说明，二者共同构成本次合并的质量证据链。

## 1. 文档控制

| 项目 | 内容 |
|---|---|
| 报告编号 | TD-FTR-20260901-05 |
| 报告版本 | 3.1（PR #3 / Cross-platform Reproducibility / Remote Verified） |
| 替代版本 | 2.2（TD-FTR-20260831-04） |
| 项目 | 面向众包内容平台的用户评价数据可信评估与分级系统（TrustData） |
| 仓库 | `SunRunJie/Trustdata-Crowdsourced-Review-Governance` |
| 被测对象 | Pull Request #3：`fix: make TrustData benchmark reproducible across Windows, macOS, and Linux` |
| PR 提交 | `5ff5d11b465e703fcc11fb9f1515144c8b6d9b85` |
| 基线提交 | `8ff6184c567edffd8f8595659d247fbb18ea7451`（`master`） |
| 本地测试时间 | 2026-09-01T12:57:23.592731+08:00 |
| 报告生成时间 | 2026-09-01T14:05:08+08:00 |
| 测试执行 | Codex 自动化测试会话 |
| 独立审计 | Research Auditor 只读交叉核验 |
| 证据等级 | E2：团队内部受控环境验证 |
| 本地技术验收 | **PASS** |
| GitHub-hosted Checks | **PASS — [TrustData CI #33467946308](https://github.com/SunRunJie/Trustdata-Crowdsourced-Review-Governance/actions/runs/33467946308)** |
| 合并门禁 | **PASS — 可以合并** |
| 项目负责人审批 | 待人工签署 |

## 2. 执行摘要与合并结论

PR #3 针对基准数据、贡献者分组、Top-K 排序、CSV 换行符及运行清单路径加入显式确定性规则，并把 CI 测试矩阵扩展到 Ubuntu、Windows 和 macOS。代码可由 GitHub 自动合并，未检测到分支冲突。

本地验收在隔离的 CPython 3.12.13 锁定环境中完成。正式全量测试 **67/67 通过**，失败、错误和跳过均为 0；竞赛材料审计 **27/27 通过**，运行清单 **18/18 个摘要通过**。第二次独立基准重建的 7 项证据测试全部通过，两次运行的 6 个核心文件 SHA-256 完全相同，支持“同平台连续运行字节级一致”的结论。

维护者批准外部贡献者工作流后，GitHub Actions 运行 `33467946308`（run number 9，attempt 2）在 PR 提交 `5ff5d11` 上完成。Ubuntu、Windows、macOS 与汇总 `CI gate` 四项检查全部成功；GitHub 随后返回 `mergeable=true`、`mergeable_state=clean`、`check_runs=4`。因此，本报告判定为：

> **本地技术验收与远端跨平台门禁均通过，PR #3 可以合并。**

本地 Windows 结果未被用来替代远端检查；Linux、macOS 与独立 Windows runner 均在同一候选提交上完成验证，形成了本地证据、三平台 CI 和汇总门禁三层证据链。

## 3. 变更范围与审查结论

### 3.1 变更规模

| 指标 | 数量 |
|---|---:|
| 提交 | 1 |
| 变更文件 | 37 |
| 新增行 | 7,447 |
| 删除行 | 7,269 |
| GitHub 冲突 | 0 |

大部分行数变化来自重新排序或重新生成的数据、证据、图表和展示文件。核心源代码变更集中在基准构建、评价、读写、标准化与流水线模块。

### 3.2 关键技术变化

| 领域 | 实现变化 | 审查结论 |
|---|---|---|
| 数据选择 | 稳定排序并加入显式并列决胜键 | 合理，消除输入顺序漂移 |
| 贡献者分组 | 分组前按 `record_id` 规范化 | 合理，减少平台/输入顺序影响 |
| Top-K 指标 | 分数降序、实体 ID 升序 | 合理，并列结果可重复 |
| CSV 输出 | UTF-8、LF、稳定行顺序 | 合理，Windows/macOS/Linux 文件一致性增强 |
| 运行清单 | 路径统一为 `/` | 合理，修复 Windows 反斜杠差异 |
| CI | 新增 `macos-latest` 矩阵项 | 配置结构通过本地解析；远端尚未执行 |
| 证据与材料 | 重新生成数字、图表、看板和说明 | 本地重建与版本化证据一致 |

### 3.3 代码审查结果

- 未发现阻塞级算法、数据泄漏、安全或分组隔离缺陷。
- 新增测试覆盖输入乱序、Top-K 并列和 CSV LF 三类关键回归点。
- `git diff --check` 通过，未发现空白错误或冲突标记。
- `requirements.lock` 未破损，`pip check` 返回 `No broken requirements found`。
- CI YAML 可解析，矩阵包含 Ubuntu、Windows、macOS，且存在汇总 `CI gate`。

## 4. 验收目标与判定标准

| 编号 | 判定标准 | 实际结果 | 状态 |
|---|---|---|---|
| AC-01 | PR 与 `master` 无冲突 | GitHub `mergeable=true` | PASS |
| AC-02 | 锁定依赖无破损 | `pip check` 通过 | PASS |
| AC-03 | 全量 pytest 无失败、错误、跳过 | 67 / 0 / 0 / 0 | PASS |
| AC-04 | 证据重建与版本化结果一致 | 7 项证据测试通过 | PASS |
| AC-05 | 竞赛材料审计通过 | 27 项检查通过 | PASS |
| AC-06 | 运行清单摘要全部匹配 | 18 个摘要通过 | PASS |
| AC-07 | 连续两次核心产物字节一致 | 6/6 SHA-256 一致 | PASS |
| AC-08 | CI 工作流包含三平台矩阵和 gate | 本地结构验证通过 | PASS |
| AC-09 | GitHub 三平台测试均成功 | Ubuntu、Windows、macOS 全部成功 | PASS |
| AC-10 | GitHub `CI gate` 成功 | Job `99755567005` 成功 | PASS |
| AC-11 | JUnit、逐例清单、元数据与报告一致 | 已更新为 67 项并绑定 PR 提交 | PASS |

AC-01 至 AC-11 全部满足，整体合并门禁为 PASS。

## 5. 测试基线与环境

| 类别 | 基线 |
|---|---|
| 项目版本 | `trustdata 0.2.0` |
| Python 约束 | `>=3.12,<3.13` |
| Python 实现 | CPython 3.12.13 |
| 操作系统 | Windows 11 10.0.26200 SP0 |
| pytest | 9.1.1 |
| NumPy / pandas / SciPy | 2.5.2 / 3.0.5 / 1.18.0 |
| scikit-learn | 1.9.0 |
| FastAPI / Starlette / HTTPX | 0.141.1 / 1.6.0 / 0.28.1 |
| 依赖锁 | `requirements.lock`，带哈希安装 |
| 测试配置 | `pyproject.toml`，仓库内 `.pytest-tmp` |
| 测试阶段网络 | 不调用真实外部 API |

确定性环境变量：

```text
PYTHONHASHSEED=0
OMP_NUM_THREADS=1
OPENBLAS_NUM_THREADS=1
MKL_NUM_THREADS=1
NUMEXPR_NUM_THREADS=1
MPLBACKEND=Agg
```

## 6. 正式执行结果

### 6.1 全量自动化测试

```text
67 passed, 1 warning in 86.75s
```

报告与机器证据写入候选树后又执行了一次最终回归，结果为 `67 passed, 1 warning in 84.18s`；随后 27 项材料审计和 18 项运行清单摘要再次全部通过。

| 测试域 | 用例数 | JUnit 用时（秒） | 覆盖重点 |
|---|---:|---:|---|
| `tests/test_control` | 5 | 0.500 | 配置脱敏、来源白名单、任务隔离、路径与写请求保护 |
| `tests/test_core` | 11 | 0.530 | 特征、评分、阈值、分组、排序、读写与跨平台确定性 |
| `tests/test_env` | 2 | 0.020 | 环境文件加载与覆盖规则 |
| `tests/test_evidence` | 7 | 81.420 | 全基准重建、指标、看板、敏感性、清单和证据镜像 |
| `tests/test_llm_mining` | 42 | 0.150 | 引用绑定、解析、抓取边界、重定向与身份去重 |
| **合计** | **67** | **82.620** | **全部通过** |

JUnit 累计用时与 pytest 墙钟时间口径不同；前者是逐例 `testcase` 时长之和，后者还包括会话初始化、fixture 和收尾。

### 6.2 材料与清单审计

| 检查 | 结果 |
|---|---|
| 必备竞赛文件存在性 | PASS |
| 申报文本长度与语言规范 | PASS |
| 30% 污染 F1 / AUPRC 与数字主表一致 | PASS |
| 5 个污染档位 × 5 个分组种子 | PASS |
| 看板 headline 与主结果一致 | PASS |
| 运行状态与版本 | PASS |
| 输入及输出哈希 | 18/18 PASS |
| 总体材料审计 | 27/27 PASS |

### 6.3 连续运行可复现性

第二次独立执行 `tests/test_evidence.py`：

```text
7 passed in 83.04s
```

两次运行的最小规范比较集：

| 文件 | SHA-256 | 一致 |
|---|---|---|
| `observed_entities.csv` | `a8e4836daf32783040379772d151fb909a2672c3d5f9cb89a34c22c89c607caf` | 是 |
| `observed_reviews.csv` | `adffcb4008e4bc42165390594e03bdf63b17dbd609635f604fbc02060c837f70` | 是 |
| `classification_metrics.csv` | `75277e14f8a5befc950128bf330bb210b10ee84f9e2ca119a61ea844587fffde` | 是 |
| `ranking_metrics.csv` | `3bd35f1f6396b152454243c344a0396d4749cd7edd9a35df16bf515f36e55c39` | 是 |
| `split_sensitivity_metrics.csv` | `b435bfe27fa0d3fecaf76a1d5ef8723446c3cd5657e650de0060ff6c5279982a` | 是 |
| `split_sensitivity_summary.csv` | `c97d4103ae077bf019e7a2573c1b25b94d5a7cf63f2ef411ca36547a8d23f96a` | 是 |

`run_manifest.json` 和 `audit_trail.csv` 含时间、环境及审计事件，不应作为跨运行字节相等的对象。

## 7. 数值影响分析

确定性排序改变了受控基准的具体样本顺序，因此版本化指标发生小幅变化。主数字、结果 CSV、看板、材料和图表已同步更新，并由证据测试交叉核对。

| 指标 | 基线 | PR #3 | 变化 |
|---|---:|---:|---:|
| 30% 污染 F1 | 0.749507 | 0.749248 | -0.000259 |
| 30% 污染 AUPRC | 0.949222 | 0.948984 | -0.000238 |
| 30% 原始平均排名误差 | 20.4565 | 20.3960 | -0.0605 |
| 30% 加权平均排名误差 | 15.2275 | 15.2335 | +0.0060 |
| 排名误差降幅 | 25.56% | 25.31% | -0.25 个百分点 |

变化幅度较小，且证据链内部一致；它反映确定性样本选择的变化，不是执行随机漂移。已知边界仍然存在：1% 低污染条件下 F1 较弱，加权排名在 1% 条件下仍有退化，材料中应继续如实披露。

## 8. GitHub Checks 与合并门禁

### 8.1 计划中的远端任务

| 任务 | 目标 |
|---|---|
| `Tests (ubuntu-latest, Python 3.12.13)` | Linux 锁定版本验证 |
| `Tests (windows-latest, Python 3.12)` | Windows runner 可用补丁版验证 |
| `Tests (macos-latest, Python 3.12)` | macOS 跨平台验证 |
| `CI gate` | 要求整个矩阵成功 |

### 8.2 当前远端状态

| 字段 | 值 |
|---|---|
| PR 状态 | open |
| Draft | false |
| `mergeable` | true |
| `mergeable_state` | clean |
| PR head | `5ff5d11b465e703fcc11fb9f1515144c8b6d9b85` |
| Check Runs | 4 |
| Actions 运行 | [33467946308](https://github.com/SunRunJie/Trustdata-Crowdsourced-Review-Governance/actions/runs/33467946308)，attempt 2 |
| 远端结论 | PASS |

| Check | Job ID | 完成时间（UTC） | 结论 |
|---|---:|---|---|
| macOS / Python 3.12 | `99754869975` | 2026-09-01T06:03:18Z | success |
| Ubuntu / Python 3.12.13 | `99754870158` | 2026-09-01T06:03:18Z | success |
| Windows / Python 3.12 | `99754870196` | 2026-09-01T06:05:02Z | success |
| `CI gate` | `99755567005` | 2026-09-01T06:05:07Z | success |

此前针对提交 `899ae3c` 的成功运行只证明旧提交的 Ubuntu/Windows 状态，不能替代 PR #3 的三平台检查。测试报告能够补充 GitHub Checks，但不能替代由独立 runner 在目标提交上执行的 Checks。

## 9. 缺陷、警告与风险登记

| ID | 级别 | 状态 | 说明 | 处置 |
|---|---|---|---|---|
| F-001 | Blocker | Closed | 外部贡献者工作流最初处于 `action_required` | 维护者已批准；三平台与 gate 全部成功 |
| W-001 | Minor | Open | FastAPI/Starlette TestClient 出现弃用警告 | 当前不影响结果；下次依赖升级评估 `httpx2` |
| L-001 | Limitation | Accepted | 未执行浏览器 E2E、负载、渗透、隐私影响和真实外部 API 测试 | 不属于本次确定性修复范围；发布前按风险补充 |
| L-002 | Limitation | Accepted | 外部绝对输出目录不属于当前 manifest 的仓库相对路径契约 | 使用项目默认仓库内运行目录；如要开放 API 再单独设计 |

审计期间两次非正式试运行因审计者覆盖了项目自带的 `--basetemp=.pytest-tmp` 约定而出现临时目录/相对路径设置错误；两次均未计入正式结果。恢复仓库标准配置后，67 项正式测试全部通过。该过程记录用于区分测试工具配置错误与产品缺陷。

## 10. 证据目录与完整性

| 证据 | 路径 | SHA-256 |
|---|---|---|
| 最终报告 | `competition/evidence/TEST_REPORT.md` | 提交时由 Git 追踪 |
| JUnit | `competition/evidence/runtime/pytest-junit.xml` | `21d29b3ba36fb156136afcfdc9c4ecb800d318de0ff4e35320c593b937246809` |
| 逐例清单 | `competition/evidence/runtime/test-case-inventory.csv` | `6e4c5b860ca358d59af273e01ac1488fd89e5b327e656b563d7e130aef200062` |
| 运行元数据 | `competition/evidence/runtime/test-run-metadata.json` | 提交时由 Git 追踪 |
| 版本化运行清单 | `competition/evidence/runtime/run_manifest.json` | 由 18 项摘要验证覆盖 |
| 依赖锁 | `requirements.lock` | `815f48d1ed9b12766900451b0584fcb2e1f0735f7d0a7a401dae531e98196e55` |
| CI 工作流 | `.github/workflows/ci.yml` | `c0a53d9099a1e594469b645b91c09d2961ed1259d89d85a56c862f320000e208` |

## 11. 可复现命令

在仓库根目录、CPython 3.12 环境中执行：

```powershell
python -m pip install --require-hashes -r requirements.lock
python -m pip check
python -m pytest --junitxml=test-results/pytest-local.xml
python scripts/prepare_observed_data.py
python scripts/run_trustdata.py
python scripts/verify_run_manifest.py
python scripts/audit_competition_package.py
```

完整流水线会生成 `outputs/runs/latest`，因此清单验证与材料审计应在流水线成功后执行。

## 12. 最终判定与签署

### 12.1 当前判定

- 本地功能、证据一致性与同平台连续运行可复现性：**PASS**。
- GitHub 跨平台执行：**PASS**。
- 当前合并判定：**PASS / 可以合并**。

### 12.2 合并条件完成情况

1. PR 候选提交已触发并完成 GitHub Actions。
2. Ubuntu、Windows、macOS 三个平台的 67 项测试全部通过。
3. `CI gate` 成功。
4. 运行链接、head SHA、完成时间和任务结论已写入本报告及 `test-run-metadata.json`。
5. 本次新增变更仅为测试报告和机器证据；若功能代码再次变化，需重新执行完整验收。

### 12.3 签署栏

| 角色 | 姓名/标识 | 结论 | 日期 |
|---|---|---|---|
| 测试执行 | Codex 自动化测试会话 | 本地 PASS | 2026-09-01 |
| 独立质量审计 | Research Auditor | 本地与远端 PASS | 2026-09-01 |
| 项目负责人 |  |  |  |

本报告覆盖 PR head `5ff5d11b465e703fcc11fb9f1515144c8b6d9b85` 及随报告一并提交的非执行性测试证据更新。任何后续功能代码、依赖或工作流变化都会使当前验收范围失效。
