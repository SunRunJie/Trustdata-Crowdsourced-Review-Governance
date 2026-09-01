# TrustData 当前状态审计

当前里程碑：数据、算法、产品与申报材料最终闭环已完成，进入实名补全与外部试点准备。

## 1. 已完成交付

| 交付项 | 状态 | 证据 |
|---|---|---|
| 项目定位与范围冻结 | 已完成 | `PROJECT_SCOPE.md`、`docs/01_COMPETITION_STRATEGY.md` |
| 前置研究复核 | 已完成 | `prior_research/`；上游提交 `88e0ab65...`；DOI `10.5281/zenodo.21955380` |
| 数据资产审计与来源边界 | 已完成 | `docs/02_DATA_ASSETS.md`、`competition/evidence/INDEX.md` |
| 十万级受控基准 | 已完成 | clean 100,000；注入 30,000；`src/trustdata/benchmark.py` |
| P/B/C/X/T 特征与场景化 DTS | 已完成 | `src/trustdata/features.py`、`src/trustdata/scoring.py` |
| 分类、排序、消融、公平性与分组敏感性评测 | 已完成 | `src/trustdata/evaluation.py`、`outputs/runs/latest/` |
| 可复现流水线与产物哈希 | 已完成 | `scripts/run_trustdata.py`、`scripts/verify_run_manifest.py` |
| 静态产品原型 | 已完成 | `product/`；数据读取 `app/data/dashboard.json` |
| 内部证明与申报证据索引 | 已完成 | `competition/evidence/`、`docs/07_REPRODUCIBILITY_AND_EVIDENCE.md` |
| 申报书 Word/PDF | 已完成（待补成员信息） | `deliverables/TrustData_2026新域新质创新大赛申报书.docx`、`.pdf` |
| 路演 PPT 与讲稿 | 已完成 | `deliverables/TrustData_2026新域新质创新大赛路演稿.pptx`、`materials/DEFENSE_DECK_OUTLINE.md` |
| 最终交付验收 | 已完成 | `competition/FINAL_ACCEPTANCE_REPORT.md`、`scripts/audit_competition_package.py` |

## 2. 当前证据口径

- 真实公开归档与受控合成基准分开存储、分开表述。
- 受控污染结果用于方法验证，证据等级为 E2；真实平台攻击率与线上效果需要独立试点数据。
- 当前版本评估数据使用风险；单条内容事实核验、生成来源认定和法律责任判断由相应专业流程承担。
- 30% 污染水平下，主模型 F1=0.7492、AUPRC=0.9490、FPR=0.0017；排序平均名次误差较原始排序下降 25.31%。五个贡献者分组种子下，F1 中位数为 0.7515，范围为 0.7443–0.7644。所有数字均可由 `competition/evidence/results/` 与运行清单复核。

## 3. 待提交前补全

1. 在申报系统填写团队、推荐单位、联系方式、知识产权与签章信息。
2. 按官方系统字段核对项目名称、领域方向和附件大小。
3. 平台合作阶段补充真实标注、影子运行与误报成本校准；计划项与已完成成果分栏记录。
4. 现场演示前启动本地静态站点并确认 `dashboard.json` 与运行清单一致。

## 4. 外部约束与已知限制

- RYM 快照的再分发许可状态待确认，公开交付提供来源、校验和、脚本及许可说明。
- 当前证据覆盖公开内容分布与受控贡献者行为；真实平台贡献级时间面板进入 E3 阶段。
- 当前产品以可离线运行的静态原型交付；公网部署需完成域名、备案、安全与隐私评估。
- Word、PDF 与 PPT 均执行逐页渲染检查；PPT 同时执行画布溢出检测。

## 5. 结论

**进入提交准备阶段**：技术、证据、产品与材料闭环已通过最终验收。提交前工作包括补齐团队信息、遵循赛事系统字段、复核附件与现场演示。新增指标需先完成验证并归档证据。
