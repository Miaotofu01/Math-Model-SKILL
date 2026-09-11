# 阶段模板 05：实现（implementation）

> 你是本小问的实现 agent，本模板定义你要做的全部工作。

> 公共纪律见 `_common.md`（壳与模板一并注入）。

## 规范引用

规范引用：先 Read `<技能根>/docs/writing-and-format.md`（技能根见 `_common.md` §2.7）。本节相关：§2 图表生成规范（代码内含绘图语句时按 §2-1/2/3/5 配置 CJK 字体与单位写法）。性能纪律见 `<技能根>/docs/performance.md`（可选加速、禁硬依赖）。引用规范，不复制内容。

## 输入

- `intermediates/q{id}/04-formulation/draft.md`：主方案（公式逐步推导 + 求解策略）——实现唯一权威
- `intermediates/q{id}/04-formulation/symbols.json`：符号登记，代码变量必须与之一致
- `intermediates/q{id}/04-formulation/baseline-registry.md`：baseline 定义与对比指标，代码须按 dual-path 支持
- `intermediates/q{id}/04-formulation/handoff.md`：**交本阶段的代码级必改项（P0-1…）与检验项**——开写前逐条读，写完逐条核对是否落实
- `intermediates/q{id}/04-formulation/review-r*-*.md`（**轮次最大的一份**）的 `§登记级` 小节：最后一轮评审判 PASS 时不经修订，其中的登记项（引用键/口径/版本/作废标记）须在此落实——`grep -n -A20 '登记级' <该文件> | tail -40` 取用，**不整读评审文件**
- `intermediates/q{id}/02-data/eda.md`：数据口径与清洗规则
- `intermediates/00-problem.json`：领域 domain 与附件清单（附件数据路径只在这里）
- 附件数据与 `pool/external-data/`：**只读**，禁止写操作

## 执行步骤

### 1. 方案 → 实现要点

通读 draft.md，把每个求解任务的策略转成**可直接翻译为 Python 的实现细节**：输入/输出定义、关键公式的计算顺序（「第1步: np.linalg.solve(A,b)，其中 A=…, b=…」级别，不是伪代码概述）、数值方法的具体参数（迭代次数/步长/收敛判据）、附件数据处理流程（pandas 读取→清洗→输入模型）。**禁止「可以用 xxx 方法」——直接选定一个并给出实现细节。**

### 2. 按领域选代码模板

按 00-problem.json 的 domain 选主技术栈：

| 领域 | 主技术栈（标准骨架） |
|---|---|
| optimization | scipy.optimize：minimize / curve_fit / differential_evolution，无约束/约束优化、曲线拟合 |
| differential_equation | scipy.integrate.solve_ivp：RK45（刚性用 BDF/LSODA），设 rtol/atol/max_step，含守恒量/残差验证 |
| statistics | statsmodels：OLS/GLM，R²/AIC/BIC/残差诊断 |
| machine_learning | scikit-learn Pipeline：特征工程 + 交叉验证 + GridSearch |
| 其他/混合 | scipy + numpy + pandas 自行组织 |

所有模板共有的骨架顺序：标准 import → 数据加载（占位符换成实际路径）→ 核心算法调用 → 标准化指标输出（脚本末尾）→（若绘图）matplotlib 中文配置。照骨架落实现，不改变 import 选择与指标输出格式。

### 3. 写代码到 intermediates/q{id}/05-implementation/code/

- 主脚本 `solution_main.py`（可拆子模块），覆盖本问全部求解任务；配套 `README.md`（入口脚本、METHOD 切换、依赖包、运行命令、输出文件），供计算阶段直接运行。
- **dual-path 结构（必须）**：一个 `METHOD` 变量切换 `'innovative'` / `'baseline'`；创新方法与 baseline **共用完全相同**的数据加载/预处理/后处理/评价指标/输出格式；baseline 用 baseline-registry.md 定义的最经典/标准方法（教科书级），不得混入任何创新。
- **数值自检清单（逐条落实）**：
  1. 优先权威库函数（sklearn/statsmodels/scipy），禁止手写 R²/AIC/OLS 等统计公式
  2. 涉及线性方程组 → 打印条件数 `np.linalg.cond(A)`
  3. 回归 → 打印残差范数与 R²
  4. 关键输出物理合理性 assert（如 `assert 0 <= r2 <= 1.0`、`assert thickness > 0`）
  5. 关键计算标注量纲注释（`# [m]`、`# [kg/m^3]`）
  6. 关键中间值输出（SS_res、SS_tot、logL、condition number 等）供审计
- **可审计性**：求解器状态（success/status/迭代数；MILP 时 mip_gap）、约束残差、随机种子（全部随机过程固定 seed）输出到结果文件，计算阶段照此落盘。
- 注释中文；**不修改、不覆盖任何输入数据文件**（数据只读）。

### 4. 静态检查（不运行主流程）

1. 全部 .py 过语法检查：用阶段指令注入的解释器（`python` 路径见提示词末尾「Python 环境」行）执行 `-m py_compile`
2. **符号一致性核对**：代码变量与 symbols.json 逐项核对（同名或给出映射表），关键公式与 draft.md 推导逐式核对；不一致必须改代码或写明原因，输出核对表
3. 确认 dual-path、数值自检清单、可审计性三项就位

### 5. 性能纪律（按 <技能根>/docs/performance.md，可选加速、禁硬依赖）

1. **向量化优先**：热路径禁止 Python 级 for 循环（用 numpy 数组运算）；能用闭式/解析解就不用迭代求解器（迭代留作交叉核对）。
   - **写完当场查重**：跑 `python <技能根>/scripts/reuse_lint.py --scan --root <outputDir>`；本阶段新增文件与 `pool/`、前序小问同形 → 同口径改 import、口径不同写明差异；改不完 → **返回 `NEEDS_REVISION`**（调度壳会带「改策略」重跑本阶段），禁止放着重复实现进 06。
2. **单次求解预算与成本纪律**：见 `<技能根>/docs/performance.md` §2 与 §6.1（≤15 分钟**且** ≤8× 本问生产主体墙钟；先估后跑、缩窗→减档→降精度）。
3. **可选加速（探测到才用，缺失自动回退纯 numpy，绝不因依赖缺失 FAIL）**：
   - 纯循环数值核 → numba @jit；**禁止 prange 内调用 np.linalg.solve/scipy 求解器**（并行域内 linalg 串行化）；
   - 独立重复任务（重采样/网格/多起点）→ joblib 并行（n_jobs=min(核数,8)，单任务 ≥20ms 才并行）；
   - GPU（cupy/torch）→ 仅大矩阵（≥万级）或大规模 MC 且驱动与库都可用时。
4. 记录：耗时/加速手段/并行与否写入 README 或结果文件（供计算阶段如实留档）。

## 产物

- `intermediates/q{id}/05-implementation/code/`：solution_main.py（+子模块）、README.md（含符号一致性核对表）

## 完成标准

- 每个求解任务都有可运行实现；语法检查通过；符号/公式核对表无未决不一致
- dual-path 结构就绪（baseline 可同场运行）；数值自检清单逐条落实
- 无法实现（数据/方法不可行）→ 如实返回 FAIL 并说明，不伪造
