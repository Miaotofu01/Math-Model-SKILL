# 性能优化规范（计算/稳健性阶段）

> 适用范围：阶段五（实现）、阶段六（计算）、阶段九（稳健性）。所有加速手段为**可选**：库缺失必须自动回退纯 numpy/scipy，**绝不因依赖缺失而 FAIL**。
> 实测依据：`test/perf/`（本仓库夹具基准，2026-09-09，24 核 + OpenBLAS；numba 0.67.0 可装可导入）。

## 0. 环境与 venv 机制（shell 注入，幂等）

- **初始化**：workflow 启动时（状态就绪后、逐问循环前）执行 `ensureEnv`：创建项目 venv `<outDir>/.venv`（已存在则复用），自动安装白名单库 `numpy scipy pandas statsmodels matplotlib openpyxl joblib numba`（限时 5 分钟，失败记录不阻塞）。
- **权威报告**：结果写 `intermediates/env-report.json`：`{problemId, python, fallback, libs{各库版本}, autoInstalled[], failed[]}`；同 problemId 已存在 → 直接复用不重装。
- **注入**：shell 把 `## Python 环境：<python 路径>` 注入每个阶段/门禁/评审/修订提示词——**所有 python 执行一律用该路径**（agent 生成的 shebang/`python3` 调用都要改成它）。
- **降级**：无网/只读/venv 失败 → `python:"python3"`、`fallback:true`，一切照旧（venv 是优化不是门槛）。
- **可复现**：`.venv/` 进 gitignore；`pip freeze` 可审计（env-report 记录版本）。

## 1. 选型规则（按收益排序）

| 手段 | 适用 | 实测增益（夹具） |
|---|---|---|
| 1. 向量化 / 闭式解 | 一切热路径（Python 循环 → numpy 数组运算） | **~230×** |
| 2. numba @jit | 纯循环数值核（n=万级以内） | **~195×** |
| 3. joblib 并行 | 单任务 ≥20ms 的**独立**重复任务（bootstrap/敏感性/网格/多起点） | 24 核 ~3-9×（受内存带宽限制） |
| 4. GPU（cupy/torch） | 大矩阵（≥万级）/ ML / 百万级 MC；**须驱动与库都可用** | 小问题反而慢（搬运开销） |

**禁用**：`numba prange` 内调用 `np.linalg.solve` / `scipy` 求解器——并行域内 linalg 串行化，实测反而慢 5 倍。

## 2. 通用纪律

- **向量化优先**：热路径禁止 Python 级 for 循环；用 numpy 数组运算（`(B,n)` 批量、广播、`einsum`）。
- **闭式/解析解优先**：能用解析式就不用迭代求解器（迭代留作交叉核对：闭式主路径 + 库函数/暴力对拍核验）。
- **预生成随机流**：bootstrap 等一次性生成全部重采样索引（`rng.integers((B,n))`），多路实现共用同一随机流 → 输出可逐位复现。
- **避免重复计算**：innovative/baseline 共用预处理；EDA 结果不重跑；同一批实验只算一次。
- **复用核心（禁重写）**：同一物理/算法核心只实现一次（题专用核心存 `pool/problem/<题>/` 并登记 manifest，或前问 `02-data`），后续一律 import 复用，禁止各自重写慢副本——实测重写核心导致单步耗时从秒级涨到 18 分钟白付；复用已优化核心可降到 ~1/6。
- **批量工具调用（减回合）**：一次 `Read` 并列读多文件、一次 bash 跑完所有检查；禁止「写→跑→改→再跑」微循环（工具往返是 agent 会话耗时主因，实测实现会话 161 次工具调用大量是微循环）。
- **单次求解预算**：默认 ≤15 分钟；超出先降样本/收敛精度（如 `rtol/atol` 放宽一档、`max_iter` 收紧），而不是无限等待。

## 3. 并行（joblib）规则

- 探测：`import joblib` 可用才用；`n_jobs = min(os.cpu_count(), 8)`（过大受内存带宽限制，实测 24 核只到 ~3×）。
- **单任务 <20ms 不并行**（进程启动开销 ~0.5-1s 吃掉收益；阈值同 §1 表）；小任务直接向量化。
- 并行 worker 内用独立子随机流（从主种子派生），结果与串行**统计一致**；需要逐位一致时走「预生成索引 + 分块」。
- 并行输出落盘后与串行基线抽查一致。

## 4. numba 规则

- 只 @jit **纯循环数值核**（输入输出为 numpy 数组），不要在 jit 函数里调 scipy 或 I/O。
- `prange` 只用于**纯元素运算**（逐元素/归约），**禁止**在 `prange` 内放 `np.linalg.solve`/`scipy.optimize`/`solve_ivp`。
- 首次调用编译预热；小任务（n<几百）编译开销可能吃掉收益，先测再决定。
- 库缺失 → 直接回退纯 numpy 循环，不 FAIL。

## 5. GPU 双路径（可选）

- 探针逻辑（零异常，缺驱动/库 → 自动 CPU 回退）：
  ```python
  import shutil, subprocess, importlib.util
  smi = shutil.which("nvidia-smi")
  gpu = smi and subprocess.run([smi, "-L"], capture_output=True).returncode == 0
  has_cupy = importlib.util.find_spec("cupy") is not None
  has_torch = importlib.util.find_spec("torch") is not None
  if gpu and (has_cupy or has_torch):
      # GPU 路径：仅当单次运算矩阵 ≥ 万级 或 大规模 MC
  else:
      # CPU 路径：向量化 → numba → joblib
  ```
- GPU 搬运开销：小问题 GPU 反而慢；显存不足（如 8GB）时拆批。

## 6. 实验预算（稳健性）

- Bootstrap：B=500–1000 足够（标准误收敛），不必 5000。
- 敏感性：只打关键参数（±10%/±20%），复用 06 已有数据。
- 消融：每组件一个 removed 变体即可。

## 7. 记录（可审计）

- 实际耗时、加速手段、并行与否写入 results.json（如 `perf: {wallTime_s, method, parallel, notes}`）与 robustness.md——供 sanity 核验与论文如实披露。

## 8. 反面教训（实测）

- `numba prange` + `np.linalg.solve`：25.6s vs 串行 4.9s（**0.2×，更慢 5 倍**）——linalg 在并行域内串行化。
- 内存带宽受限负载（大样本随机访问重拟合）24 核并行只 ~3×：并行不是银弹，先向量化。
- 小任务并行（B=5000 单核 10 元素）：joblib 仅 9× 且低于向量化 231×。
