# 阶段模板 05：实现（implementation）

> 你是本小问的实现 agent，本模板定义你要做的全部工作。调度壳已注入：当前小问 ID（ctx 中的 `q`，如 `q1`）、模式（full/quick）、依赖与产物路径。下文路径中 `q{id}` 替换为 ctx 中的小问 ID；所有相对路径基于 outputDir 根。

> 公共纪律（统一节拍 / 工具纪律 / 数字单一真源 / 复用 / 工具与文档路径）见 `_common.md`——**与本模板同一次并列 Read 读入**。

## 规范引用

先 Read `<技能根>/docs/writing-and-format.md`（`<技能根>` = 阶段指令里给出的技能根；该文件缺失时按技能根向上/向下探测 `docs/`）。本节相关：§二 图表生成规范（代码内含绘图语句时按 §二-1/2/3/5 配置 CJK 字体与单位写法）。性能纪律见 `docs/performance.md`（可选加速、禁硬依赖）。引用规范，不复制内容。

## 输入

- `intermediates/q{id}/04-formulation/draft.md`：主方案（公式逐步推导 + 求解策略）——实现唯一权威
- `intermediates/q{id}/04-formulation/symbols.json`：符号登记，代码变量必须与之一致
- `intermediates/q{id}/04-formulation/baseline-registry.md`：baseline 定义与对比指标，代码须按 dual-path 支持
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

### 5. 性能纪律（按 docs/performance.md，可选加速、禁硬依赖）

0. **Python 环境**：所有 python 执行一律用调度壳注入的环境路径（阶段指令首行 `## Python 环境`，以 `intermediates/env-report.json` 为准（文件不存在 → 用系统 python3））；依赖缺失 → 优先 venv 安装、失败降级纯 numpy/scipy，**绝不因缺库 FAIL**。
1. **复用核心实现（禁止重写）**：若 `pool/` 或前序小问已有**同口径**的核心实现（如判据/求解器等核心算法；查 `pool/manifest.json`、`pool/problem/manifest.json`，以及前序小问的 `02-data/`、`05-implementation/code/`、`06-computation/`），必须 import 复用，**禁止各自重写新副本**（重写会重复踩慢实现且口径漂移）；**复用前必须核对常量/维度/场景作用域与本问一致（如单机核心不得用于多机题），不一致禁止复用**；口径不一致才允许新实现，并在 README 写明差异与原因。
   - **通用原语**：先 `--list` 查技能根现有条目（几何/区间等「库不提供且口径敏感」的原语）；命中 → 首次 `cp <技能根>/scripts/primitives.py pool/primitives.py`（`--selftest` 应全绿）后一律 import（**路径口径**：`PYTHONPATH=<outputDir>/pool:<outputDir>` 或 `pc.bootstrap_sys_path()`；撞 ModuleNotFoundError 先修路径，禁止内联抄代码）；未命中 → 按 `_common.md` §5.1 判据实现，**单题条目写 `pool/problem/<题>/`（参数外置 `const.json`），不进技能根**
   - **重计算/敏感性实验** → 走探针池 `probes/<角色>/<目的>.py` + `probe_cache.py`（见 `_common.md` §5.2），禁止 `/tmp` 一次性脚本
2. **向量化优先**：热路径禁止 Python 级 for 循环（用 numpy 数组运算）；能用闭式/解析解就不用迭代求解器（迭代留作交叉核对）。
   - **写完当场查重**：跑 `python <技能根>/scripts/reuse_lint.py --scan --root <outputDir>`；本阶段新增文件与 `pool/`、前序小问同形 → 同口径改 import、口径不同写明差异；改不完 → **返回 `NEEDS_REVISION`**（调度壳会带「改策略」重跑本阶段），禁止放着重复实现进 06。
3. **单次求解预算**：默认 ≤15 分钟；超出先降样本/放宽收敛精度（rtol/atol/max_iter），不无限等待。
4. **可选加速（探测到才用，缺失自动回退纯 numpy，绝不因依赖缺失 FAIL）**：
   - 纯循环数值核 → numba @jit；**禁止 prange 内调用 np.linalg.solve/scipy 求解器**（实测反而慢 5 倍）；
   - 独立重复任务（重采样/网格/多起点）→ joblib 并行（n_jobs=min(核数,8)，单任务 ≥20ms 才并行）；
   - GPU（cupy/torch）→ 仅大矩阵（≥万级）或大规模 MC 且驱动与库都可用时。
5. 记录：耗时/加速手段/并行与否写入 README 或结果文件（供计算阶段如实留档）。
6. **批量工具调用（减回合，agent 会话耗时主因）**：一次 `Read` 并列读入全部所需文件（多路径一次读完）；一次 bash 执行全部静态检查/冒烟测试；**禁止「写一小段→跑→改→再跑」的微循环**——先完整落盘再统一运行验证。实测同类会话 161 次工具调用中大量是微循环往返。

## 产物

- `intermediates/q{id}/05-implementation/code/`：solution_main.py（+子模块）、README.md（含符号一致性核对表）

## 完成标准

- 每个求解任务都有可运行实现；语法检查通过；符号/公式核对表无未决不一致
- dual-path 结构就绪（baseline 可同场运行）；数值自检清单逐条落实
- 无法实现（数据/方法不可行）→ 如实返回 FAIL 并说明，不伪造
