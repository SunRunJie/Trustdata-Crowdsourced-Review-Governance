# 内部测试报告

证据性质：项目团队内部自动化测试，等级为 E2。

## 结果

执行 `PYTHONPATH=src python -m pytest -q`，结果为 `13 passed`。

| 测试 | 核验内容 | 结果 |
|---|---|---|
| feature range / missingness | P/B/C/X/T 范围与缺失处理 | 通过 |
| new-account weak signal | 新账号作为弱特征参与联合判断 | 通过 |
| duplicate detection | 精确重复组计算 | 通过 |
| score/tier/coverage | DTS、等级、覆盖度一致性 | 通过 |
| scenario weights | 场景权重和为 1 | 通过 |
| CSV/JSON roundtrip | 权威交换格式读写 | 通过 |
| threshold FPR constraint | 验证阈值选择满足清洁样本误伤约束 | 通过 |
| contributor group split | 贡献者跨训练、验证、测试组隔离 | 通过 |
| numbers master consistency | 数字母表与 30% 主结果一致 | 通过 |
| dashboard consistency | 看板头部指标与结果 CSV 一致 | 通过 |
| split sensitivity coverage | 五个分组种子和五档污染完整 | 通过 |
| manifest digests | 运行清单所列输出哈希一致 | 通过 |
| evidence mirror | 正式证据镜像与最近运行结果一致 | 通过 |

## 待覆盖项目

- 数据生成种子层面的区间估计。
- 大规模性能与内存压力测试。
- 浏览器自动化和无障碍测试。
- 真实平台数据的效度与公平性测试。
- 安全、渗透和隐私影响评估。

本报告支持“13 项自动化测试通过”，其余项目按待覆盖清单推进。
