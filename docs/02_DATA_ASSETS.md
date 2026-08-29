# 数据资产、字段与许可边界

## 数据规模

本项目采用有来源记录、许可说明和版本校验的数据接管方案。现阶段对前置研究仓库中的公开归档进行可复核接管：26 个文件、17 个 CSV、64,243,618 字节；清洗后形成 42,356 条实体平台记录和 166,259 条非空评论记录，共 208,615 条观测记录。另构建 100,000 条清洁基准记录及最多 30,000 条受控注入记录。

| 资产 | 行数 | 用途 | 许可/再发布 |
|---|---:|---|---|
| AOTY / Metacritic 历史评分 | 32,358 原始；32,356 可规范化 | 历史实体与跨源参考 | 源文件声明 GPL-2.0；再发布须保留许可 |
| AOTY Top 5000 | 5,000 | 2024 截面、跨源匹配 | 源文件声明 CC BY 3.0；需署名 |
| RYM Top 5000 | 5,000 | 跨源一致性参考 | 许可状态待确认；现阶段保留在内部研究环境 |
| 已发表乐评摘录训练集 | 116,384 | 文本多样性与重复结构基线 | 按原仓库说明用于研究，保留第三方来源和许可信息 |
| 已发表乐评摘录测试集 | 49,879 | 文本多样性与重复结构基线 | 同上 |
| 旧合成文本 | 17,274 | 前置研究遗留 | 仅用于回归检查，效能证明采用本轮受控基准 |

## 观测摘要

- 唯一规范化实体：34,584
- AOTY–RYM 跨源对齐实体：4,102
- 评论来源：131
- 规范化后文本精确重复：965 组内记录
- 评论正文缺失：0（两份原始文件各有 2 个缺失，在规范化入口被剔除）
- 观测数据支持描述性基线和内容/实体参考；贡献者纵向行为与真实攻击标签将在平台试点数据中补充。

## 核心字段

### observed_entities

| 字段 | 类型 | 含义 |
|---|---|---|
| record_id | string | 来源记录的稳定哈希 ID |
| entity_id | string | 规范化 artist + title 的稳定实体 ID |
| platform | category | AOTY、AOTY_history 或 RYM |
| title / artist | string | 规范化前可读实体字段 |
| release_year | nullable integer | 年份；来源信息模糊时记录为空值 |
| rating_norm | nullable float | 映射到 0–100 的评分 |
| rating_count | nullable integer | 平台可见评分数量 |
| critic_score / user_score | nullable float | 原平台维度；缺失状态按原记录保留 |
| source_file | string | 可追溯到原文件的相对路径 |

### observed_reviews

| 字段 | 类型 | 含义 |
|---|---|---|
| review_id | string | 稳定哈希 ID |
| source | category | 出版物/评论来源 |
| artist / album | string | 关联实体文本 |
| review_text | string | 原始摘录文本 |
| text_norm | string | 仅用于结构分析的规范化文本 |
| text_hash | string | 精确重复检测哈希 |
| source_file | string | 原文件路径 |

### benchmark_records

| 字段组 | 关键字段 | 说明 |
|---|---|---|
| 标识 | record_id, entity_id, contributor_id | 合成 ID 与实体关联 |
| 事件 | rating, review_text, created_at | 评分、文本与时间 |
| 账户 | account_age_days, profile_verified | 受控合成行为属性 |
| 来源 | source_platform, provenance_present | 来源/元数据状态 |
| 标签 | ground_truth_risk, attack_type, is_synthetic | 仅来自注入机制 |
| 角色 | benchmark_role | clean / injection，禁止与真实标签混淆 |

## 采集扩展协议

下一阶段按 `source → snapshot → normalize → validate → license → publishability` 管线接入新增来源。新增规模服从许可、可追溯性和研究设计需要。每个源保存访问记录、原始 URL、许可文本快照、请求参数或导出方式、文件哈希、字段版本、个人信息风险和再发布状态。许可与平台授权状态决定使用范围；来源状态待确认的数据保留在合规的内部研究环境。

## 数据泄漏防护

- 分组划分：同一 contributor 固定在单一训练、验证或测试分组。
- 阈值只在验证集锁定，测试集只做一次性评估。
- 合成攻击类型与时间机制相互分离，避免所有攻击共享“最近 7 天”捷径。
- 观测文本提供分布与模板种子；风险标签来自受控注入机制。
- 所有原始数据保持只读；派生结果写入 `data/processed` 和 `outputs/runs`。
