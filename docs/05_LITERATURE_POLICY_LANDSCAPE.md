# 研究、标准与政策证据图谱

结论依据官方标准、政策原文和论文原文；二手营销材料仅用于线索发现。

## 结论一：内容或语言特征适合承担局部风险识别

Mukherjee 等对 Yelp 过滤评论的研究发现，在现实 Yelp 数据中，行为特征表现较好；在众包伪评论上表现强势的语言特征迁移到现实数据后效果有限。TrustData 因此联合 B/C 多维证据。当前合成行为基准提供方法验证，真实平台效果将在标注数据上评估。

- Mukherjee, A. et al. (2013). [What Yelp Fake Review Filter Might Be Doing?](https://doi.org/10.1609/icwsm.v7i1.14389)

## 结论二：协同关系、稀缺标签和时间异常是独立信号源

Danilchenko 等将机器学习与图消息传递结合，应对可靠标签稀缺；Ye 等指出静态离线方法可能掩盖活动期间的异常，提出时间多变量信号；CARE-GNN 研究进一步说明欺诈者会进行特征和关系伪装。它们共同支持 TrustData 的 B/T 维度与未来异构图路线。当前实现采用逻辑回归，异构图模型列入下一代路线。

- Danilchenko, K. et al. (2022). [Opinion Spam Detection: A New Approach Using Machine Learning and Network-Based Algorithms](https://doi.org/10.1609/icwsm.v16i1.19278)
- Ye, J. et al. (2016). [Temporal Opinion Spam Detection by Multivariate Indicative Signals](https://doi.org/10.1609/icwsm.v10i1.14801)
- Dou, Y. et al. (2020). [Enhancing Graph Neural Network-based Fraud Detectors against Camouflaged Fraudsters](https://arxiv.org/abs/2008.08692)

## 结论三：概率分数需要校准和不确定性披露

Guo 等系统讨论了现代神经网络置信度失配，并验证温度缩放等后处理校准方法。TrustData 因此同时报告 Brier/ECE、coverage 和 uncertainty；风险概率用于相对排序，现实概率解释需要平台数据校准。

- Guo, C. et al. (2017). [On Calibration of Modern Neural Networks](https://proceedings.mlr.press/v70/guo17a.html)

## 结论四：数据质量应按用途与全生命周期管理

ISO/IEC 5259-1:2024 为分析与机器学习数据质量提供术语和系列框架，并强调数据质量与预期用途相适配。TrustData 的“场景化 DTS”正是对 fit-for-purpose 思路的工程化：同一条记录用于榜单、训练集或运营看板时，风险成本和维度权重不同。

- ISO. [ISO/IEC 5259-1:2024 — Data quality for analytics and ML](https://www.iso.org/standard/81088.html)

## 结论五：来源标识提供来源证据，其效力有明确边界

C2PA 规范通过可验证声明记录数字资产来源和编辑历史；中国《人工智能生成合成内容标识办法》要求服务提供者处理显式/隐式标识、元数据核验和传播环节提示。TrustData 的 P 维度可以接入这些来源声明。标识状态作为来源证据使用，内容事实仍由独立核验流程判断。

- C2PA. [C2PA Specifications 2.4](https://spec.c2pa.org/specifications/)
- 国家互联网信息办公室等. [《人工智能生成合成内容标识办法》](https://www.cac.gov.cn/2025-03/14/c_1743654684782215.htm)

## 差异化判断

现有研究分别讨论文本欺骗、行为异常、图关系、时间突发、概率校准和来源凭证。TrustData 以记录在特定业务中的可用性为评估对象，在一个治理流程中联合多维证据、覆盖度、不确定性、分级动作、排序稳健性和审计记录。项目的差异主要位于系统设计和治理流程层面。

当前证据支持“形成面向 UGC 数据资产治理的差异化技术组合”。“国际首创”或“国内首创”属于系统检索和第三方查新完成后的结论。
