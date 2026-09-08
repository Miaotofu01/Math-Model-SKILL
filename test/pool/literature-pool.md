# 文献共享池（literature-pool）

> 用法：后续小问先 Read 本池，只对新增主题做补充搜索；新来源**追加**，不覆盖。格式：标题+URL+角度+相关性+精读摘要+局限要点。

## q1（题目 A：人口线性外推预测 + 95% 区间）

### [1] 牛海鹏, 宋建蕊. 基于一元线性回归和GM(1,1)模型的农村人口预测. 农村经济与科技, 2013(02)
- URL: https://www.cnki.com.cn/Article/CJFDTotal-NCJI201302050.htm
- 角度: ③ 中文核心 ｜ 相关性: high
- 精读摘要: 焦作 2004-2011 农村人口与年份显著相关；一元线性回归与 GM(1,1) 并用预测（全文付费墙，仅摘要）。
- 局限要点: 单看 R² 选模不够，需对照模型与留一验证；线性假设在长期外推下过强。

### [2] Real Statistics Using Excel — Confidence and prediction intervals for forecasted values
- URL: https://real-statistics.com/regression/confidence-and-prediction-intervals/
- 角度: ② 海外方法 ｜ 相关性: high
- 精读摘要: 一元回归置信区间（回归线）与预测区间（单点）公式；对具体 x0 预测区间比置信区间更有意义且更宽。
- 局限要点: 均值置信区间≠预测区间，误用会低估不确定性；区间依赖正态/同方差假设。

### [3] L. Belzile, lineaRmodels §4.1 Confidence and prediction intervals（线性模型讲义）
- URL: https://lbelzile.github.io/lineaRmodels/confidence-and-prediction-intervals.html
- 角度: ② 海外方法 ｜ 相关性: high
- 精读摘要: 预测区间矩阵公式 x'β̂ ± t·√(s²[1+x'(X'X)⁻¹x])；正确模型下新观测约 95% 落入；区间随 x 远离均值双曲变宽。
- 局限要点: 外推点离均值越远区间越宽——外推风险的结构性来源。

### [4] FilTheo, PI-Estimators-for-ML-and-Statistical-Models（GitHub/R 综述）
- URL: https://github.com/FilTheo/PI-Estimators-for-ML-and-Statistical-Models
- 角度: ② 海外方法 ｜ 相关性: medium
- 精读摘要: 预测区间度量预测不确定性；综述统计（ETS 等）与 ML 模型的 PI 估计技术、优缺点与实现建议。
- 局限要点: 点预测不足、区间必配；正态近似在小样本下覆盖率存疑，可换 bootstrap/conformal。

### [5] Abeysinghe, Balasooriya, Tsui. Small-Sample Forecasting: Regression or ARIMA Models? 2003（DOI 10.1007/BF03404652）
- URL: https://doi.org/10.1007/BF03404652
- 角度: ② 海外方法 ｜ 相关性: medium
- 精读摘要: 小样本下回归 vs ARIMA 预测对比研究（摘要被出版社遮蔽，仅题录核实）。
- 局限要点: 小样本（n=10 级）方法选择需比较而非默认线性；自相关存在时线性回归区间偏窄。

### [6] statsmodels OLSResults.get_prediction 官方文档 v0.14.4
- URL: https://www.statsmodels.org/v0.14.4/generated/statsmodels.regression.linear_model.OLSResults.get_prediction.html
- 角度: ④ 开源代码 ｜ 相关性: high
- 精读摘要: get_prediction 返回 PredictionResults，可算均值置信区间与新观测预测区间，支撑"预测可代码复现"。
- 局限要点: 区间质量取决于模型假设是否成立；接口本身不校验残差诊断。

### [7] 城镇化进程中洛阳市人口发展的数学建模探讨（万方题录 sxjmjyqyy201402004）
- URL: https://d.wanfangdata.com.cn/periodical/sxjmjyqyy201402004
- 角度: ③ 中文核心 ｜ 相关性: medium
- 精读摘要: 仅题录，全文未取到（付费墙）。
- 局限要点: 未精读，写作阶段引用前需核实全文。

### [8] Columbia Statistical Modeling — Population forecasting for small areas（2024-04）
- URL: https://statmodeling.stat.columbia.edu/2024/04/25/population-forecasting-for-small-areas-an-example-of-learning-through-a-social-network/
- 角度: ② 海外方法 ｜ 相关性: medium
- 精读摘要: 未读到（HTTP 403）；主题为小区域人口预测的不确定性。
- 局限要点: 未精读，不建议引用。
