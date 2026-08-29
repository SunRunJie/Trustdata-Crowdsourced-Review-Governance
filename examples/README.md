# TrustData 示例输入

`sample_reviews.csv` 使用 0–5 标准评分量表，包含来源、行为、内容、跨源和时序证据所需的示例字段。示例只用于验证输入适配与解释输出，不代表真实平台攻击率或模型线上效果。

运行：

```powershell
.\.venv\Scripts\python.exe scripts\assess_data.py `
  --input examples\sample_reviews.csv `
  --output outputs\examples\sample_scored.csv `
  --scenario ranking_integrity
```

输出包括逐记录评分文件和相邻的 `sample_scored.summary.json`。缺失可选字段不会被虚构填充，而会降低相应维度覆盖度与置信度。
