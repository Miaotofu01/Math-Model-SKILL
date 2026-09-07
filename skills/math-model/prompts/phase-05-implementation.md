# 阶段模板 05：实现（implementation）

> 你是本小问的实现 agent，本模板定义你要做的全部工作。调度壳已注入：当前小问 ID（ctx 中的 `q`，如 `q1`）、模式（full/quick）、依赖与产物路径。下文路径中 `q{id}` 替换为 ctx 中的小问 ID；所有相对路径基于 outputDir 根。

## 统一节拍

1. 读 intermediates/state.json：确认前置门禁（gates 中前置阶段为 PASS），否则返回 {status:"FAIL", ...}
2. 读依赖文件（本阶段的 deps，路径已由调度壳注入）
3. 执行本阶段任务，写产物到指定路径
4. 更新 state.json 对应字段 + 追加 intermediates/ledger.md 一行
5. 返回 {status:"PASS|DRAFT|NEEDS_REVISION|FAIL|SKIPPED", artifact_path, summary≤200字}

## 规范引用

先 Read `skills/math-model/docs/writing-and-format.md`（如不可用，按调度壳的模板目录向上找 `docs/`）。本节相关：§二 图表生成规范（代码内含绘图语句时按 §二-1/2/3/5 配置 CJK 字体与单位写法）。引用规范，不复制内容。

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

1. 全部 .py 过 `python3 -m py_compile` 语法检查
2. **符号一致性核对**：代码变量与 symbols.json 逐项核对（同名或给出映射表），关键公式与 draft.md 推导逐式核对；不一致必须改代码或写明原因，输出核对表
3. 确认 dual-path、数值自检清单、可审计性三项就位

## 产物

- `intermediates/q{id}/05-implementation/code/`：solution_main.py（+子模块）、README.md（含符号一致性核对表）

## 完成标准

- 每个求解任务都有可运行实现；语法检查通过；符号/公式核对表无未决不一致
- dual-path 结构就绪（baseline 可同场运行）；数值自检清单逐条落实
- 无法实现（数据/方法不可行）→ 如实返回 FAIL 并说明，不伪造
