# 复现、版本与证据管理

## 复现步骤

```powershell
# 数据画像
.\.venv\Scripts\python.exe scripts\profile_prior_data.py

# 观测数据标准化
.\.venv\Scripts\python.exe scripts\prepare_observed_data.py

# 基准、算法与完整评估
.\.venv\Scripts\python.exe scripts\run_trustdata.py --config configs\trust.yaml

# 单元测试
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m pytest -q
```

预期：画像 26 个文件；实体 42,356；评论 166,259；基准清洁 100,000、注入 30,000；五档污染与五个贡献者分组种子完成；67 项自动化测试通过。Windows、macOS 和 Linux 的具体命令与确定性边界见 [跨平台复现说明](CROSS_PLATFORM_REPRODUCIBILITY.md)。

## 关键入口

- 数据接管：`scripts/profile_prior_data.py`
- 标准化：`scripts/prepare_observed_data.py`
- 全流程：`scripts/run_trustdata.py`
- 参数：`configs/trust.yaml`
- 核心包：`src/trustdata/`
- 测试：`tests/test_core.py`
- 结果：`outputs/runs/latest/`
- 分组敏感性：`outputs/runs/latest/split_sensitivity_metrics.csv`、`split_sensitivity_summary.csv`
- 产品：`product/`
- 前置研究：`prior_research/`，固定上游提交 `88e0ab65d96ee457b500cf5426987f691ea4b1ea`

## 运行环境

- Python 3.12.13
- numpy 2.5.2
- pandas 3.0.5
- scipy 1.18.0
- scikit-learn 1.9.0
- matplotlib 3.11.1
- PyYAML 6.0.3
- pytest 9.1.1

`pyarrow` 安装包的 wheel 哈希与预期值存在差异。基础交付因此以 CSV/JSON 为权威格式；Parquet 在兼容引擎完成校验后启用。

## 证据规则

1. 申报和路演数字只从 `competition/evidence/NUMBERS_MASTER.csv` 引用；每个对外展示的关键指标必须有独立编号，并由自动化测试与原始运行产物逐项核对。
2. 每个强主张必须在 `CLAIM_EVIDENCE.csv` 有证据路径和等级。
3. E2 表述统一为“团队内部受控评测”；E3/E4 需要对应的外部测试或运行证据。
4. 代码清单记录可核验的作者与第三方依赖；作者归属由团队确认。
5. 每次正式运行生成 SHA-256 清单，所有列出的哈希必须可直接复核。
6. 原始数据保持只读；来源许可状态决定公开再发布范围。

## 当前验收状态

- 数据画像：通过。
- 算法全流程：通过，最近一次运行约 27 秒。
- 自动化测试：67/67 通过，覆盖核心函数、环境配置、本地控制台安全回归、LLM 数据采集边界、跨平台确定性、阈值约束、分组隔离、数字口径、看板口径、分组敏感性、运行哈希与证据镜像。
- 产品页面与数据端点：HTTP 200。
- 真实平台离线标注：下一阶段。
- 平台影子部署：下一阶段。
- 第三方测试：后续验证。
