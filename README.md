# TrustData

**面向众包内容平台的用户评价数据可信评估与分级系统**

TrustData 面向 UGC 平台的数据运营与治理场景，将用户评价的行为、内容、跨源和时序信号统一为 Trust Vector，输出场景化 Data Trust Score、A–E 等级、风险标签、建议动作和可核验运行清单。

## 最终成果

- `product/index.html`：最终产品看板。
- `product/control.html`：本机全流程控制台。
- `deliverables/TrustData_2026新域新质创新大赛路演稿.pptx`：最终路演展示。
- `outputs/runs/latest/`：最终指标、图表、信任护照与运行清单。
- `src/trustdata/`：可信评估、基准、评测与控制台实现。

## 运行入口

Python 3.12 环境安装 `requirements.txt` 后，在项目根目录启动：

```powershell
python scripts/serve_solution.py
```

访问 `http://127.0.0.1:8000/`。静态展示也可直接打开 `product/index.html`。

## 边界

系统输出是指定用途下的数据使用风险建议，不直接认定用户意图，也不自动执行不可逆处罚。
