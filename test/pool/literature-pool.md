# 共享文献池（literature-pool）

> 用途：跨小问共享文献条目，避免重复检索。追加式维护：后续小问只**追加**新来源，不覆盖已有条目。
> 字段：标题 + URL + 检索角度 + 相关性 + 精读摘要 + 局限要点。

## q1 贡献条目

### [1] 基于线性回归模型、马尔萨斯人口增长模型及 logistic 模型的全国人口预测
- 角度：中文核心 | 相关性：high
- URL：https://www.sinomed.ac.cn/article.do?ui=2024176458
- 精读摘要：赵天伟、陈惠达（广东医科大学学报 2023,41(6)）用 1949–2014 数据依次建线性回归、马尔萨斯、logistic 三模型，以相对误差评价并预测 2020–2040；发现我国人口增长率呈下降趋势。三模型对比选优流程可直接支撑「说明模型选取依据」。
- 局限要点：多模型对比只在长序列下有效；增长率下降 → 线性外推长时域有系统偏差。

### [2] Evaluating Methods for Short to Medium Term County Population Forecasting（ESRI WP143）
- 角度：海外方法 | 相关性：high
- URL：https://ideas.repec.org/p/esr/wpaper/wp143.html
- 精读摘要：Morgenroth (2002) 用 1991–1996 历史误差评价多种县级人口预测方法，结论是简单份额外推不逊于队列-构成模型（"simple share extrapolation techniques perform well compared with the more elaborate cohort component model"）。支持短中期小区域外推用简单模型。
- 局限要点：简单外推仍有可测 forecast error；需以误差口径评价方法。

### [3] Bayesian Matrix Factor Models for Demographic Analysis Across Age and Time（arXiv:2502.09255）
- 角度：前沿学术 | 相关性：medium
- URL：https://arxiv.org/abs/2502.09255
- 精读摘要：Zens (2025) 用贝叶斯矩阵因子模型对多群体×年龄×时间人口矩阵做低维因子分解，MCMC 推断，预测优于标准基准；需面板数据。
- 局限要点：数据要求高，单县 10 年总量序列不可用——反面支撑低参数模型选择。

### [4] Confidence and Prediction Intervals in Data Science（LMK89, GitHub）
- 角度：开源代码 | 相关性：high
- URL：https://github.com/LMK89/Machine-Learning-MD/blob/main/Data-Science/Confidence%20and%20Prediction%20Intervals%20in%20Data%20Science.md
- 精读摘要：给出 OLS 预测区间标准误公式（含 1/n 与 (x₀−x̄)² 项，t_{n−2} 临界值）与可运行 Python 代码；明确预测区间宽于置信区间。
- 局限要点：依赖正态/同方差/独立假设；小样本下区间覆盖对假设违反敏感。

### [5] statsmodels RegressionResults.get_prediction 官方文档
- 角度：开源代码 | 相关性：high
- URL：https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.RegressionResults.get_prediction.html
- 精读摘要：官方 API 文档；一次计算预测值、预测方差、均值置信区间与新观测预测区间（mean_ci / obs_ci），适合论文代码复现。
- 局限要点：输出基于 OLS 正态理论，不覆盖模型设定误差。

### [6] Empirical Prediction Intervals for County Population Forecasts（Rayer, Smith & Tayman 2009）
- 角度：海外方法 | 相关性：medium
- URL：https://ideas.repec.org/a/kap/poprpr/v28y2009i6p773-793.html（DOI:10.1007/s11113-009-9128-7）
- 精读摘要：期刊题录（摘要不可获取）；依据历史外推误差构造县级人口预测经验预测区间（keywords: Forecast uncertainty, Accuracy）。
- 局限要点：无直接引文；作为解析区间之外的替代方案对照。

### [7] Uncertainty in population projections: the state of the art（Meireles et al.）
- 角度：海外方法 | 相关性：medium（不可访问）
- URL：https://www.semanticscholar.org/paper/12c7d664b45fc3c6ac3b13990e32a6c36e4f136a
- 精读摘要：正文/摘要均无法获取（OA 网关 502、数据库 JS 拦截），claims 留空，标 unreliable。
- 局限要点：无。

### [8] Population-Forecast-Prediction / WildTrack（Vivek-Tate, GitHub）
- 角度：开源代码 | 相关性：low
- URL：https://github.com/Vivek-Tate/Population-Forecast-Prediction
- 精读摘要：ML + 时间序列种群预测项目（5 年历史 + 卫星估计，外推 12 个月）；README 部分可见。
- 局限要点：数据驱动 ML 需多源/高频数据，对本问数据量不适用。
