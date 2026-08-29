# Dependency-aware Task Tree

## P0 — 真实性与规格（已完成）

1. 完成来源文件 profile、哈希和许可清单。
2. 固化标准 schema、缺失策略和统计规格。
3. 建立严格运行清单：输入版本、代码提交、配置、随机种子、产物与失败状态。

完成标准：任意结果可以追溯到唯一输入、配置和脚本。已由运行清单与来源证明覆盖。

## P1 — 数据与算法闭环（已完成）

1. 全量规范化可复用真实归档。
2. 生成明确标注的十万级 contribution benchmark。
3. 实现 P/B/C/X/T 与 evidence coverage。
4. 实现场景化 DTS、tier、治理动作和审计记录。
5. 完成基线、主模型、消融、敏感性、公平性与排序恢复实验。

完成标准：一条命令从输入生成全部指标、表和产品数据，失败时返回非零退出码。已通过 `scripts/run_trustdata.py` 与 13 项测试。

## P2 — 产品（首版已完成）

1. Overview。
2. Trust Explorer / Trust Passport。
3. Risk & Temporal Monitor。
4. Cross-source Analysis。
5. Governance Center / Review Queue / Audit Trail。
6. Benchmark 页面与现场演示脚本。

完成标准：本地可运行，展示数据由本轮产物动态读取。当前以静态原型交付，公网部署列入后续工程任务。

## P3 — 证据与申报（首版已完成）

1. 事实库、数字主表、术语表与 Claim-Evidence Matrix。
2. 技术成果说明、数据来源证明、算法验证、受控污染实验、内部系统测试与复现说明。
3. 申报书栏目、Word/PDF、图表、证明材料索引。
4. PPT、Demo Script、FAQ 和红队问题库。

完成标准：正文数字与产物一致；合成/真实、已完成/计划、团队/第三方边界无冲突。申报书仍需补齐团队与签章信息。

## P4 — 最终验收（提交前执行）

1. 独立数值审计（已完成首轮，提交前再复核）。
2. 代码与文档复现测试（已完成主流程）。
3. 匿名评审与红队审稿（待团队最终定稿后执行）。
4. 页面、图表、Word、PDF、PPT 的视觉与术语一致性检查（PDF/PPT 已完成，Word 需在可用 Office 环境复核）。
