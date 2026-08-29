# TrustData

**正式项目名称：面向众包内容平台的用户评价数据可信评估与分级系统**

TrustData 面向 UGC 平台的数据运营与治理团队，评估一条或一批评价数据在特定下游场景中值得被怎样使用，并保留可复核的证据链。音乐评价平台是首个验证场景。

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
