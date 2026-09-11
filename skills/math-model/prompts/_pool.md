# 代码池手册（原语池 / 题专用核心）

> 本文件由调度壳**只对写代码的阶段**一并注入（阶段 02/04/05/06/07/08/09）；其余阶段不必读。
> 复用纪律的通用部分与探针池见 `_common.md` §5。

### 5.1 原语池（题无关，可跨题带走）

- 规范源：`<技能根>/scripts/primitives.py`——**只装机制与判据，不装任何单题内容**（条目以 `--list` 为准）。可进本文件者须同时满足「库不提供 + 口径敏感 + 领域中立（纯数学定义，不含题目建模选择）」，且已有 ≥2 个不同题的复用证据；单题条目写 `pool/problem/<题>/`。`--selftest` 自带**暴力对拍**，`--manifest` 出对拍值与实测耗时
- 首次使用：`cp <技能根>/scripts/primitives.py pool/primitives.py`，此后 run 内一律 `import` 复用（run 级副本保证产物自包含）；`python pool/primitives.py --manifest pool/manifest.json` 生成清单（签名/单位约定/返回语义/依赖/版本/对拍值/实测耗时）
- 改原语必须 `--selftest` 全绿 + 在 manifest 递增版本号（版本参与探针缓存指纹）
- 题专用实现（运动学、决策变量域、目标函数、判据口径）写 `pool/problem/<题>/*.py`，题目参数外置 `const.json`；**不要**塞进题无关原语
- 题专用核心**必须登记** `pool/problem/manifest.json`（手写，无工具生成）：`{"entries":{"<模块.函数>":{"口径":"<一句话>","单位":"…","被复用":["q1","q4"],"对拍值":"<可选>"}}}`——它是后问发现「已有同口径实现」的唯一入口
- **改池必须递增版本**：编辑 `pool/primitives.py` 后重跑 `--manifest`，**退出码 1 表示「内容变了但 VERSION 未递增」**（会让探针缓存静默命中过期结论）→ 递增 VERSION 后重跑，**不是工具故障、不要跳过**
- **import 路径口径**：脚本不在 `pool/` 里时 `import primitives` 默认会失败（Python 只把**脚本所在目录**放进 `sys.path`，不是 cwd）→ 用 `PYTHONPATH=<outputDir>/pool:<outputDir> python …`，或脚本首行 `import probe_cache as pc; pc.bootstrap_sys_path()` 后再 import 池；走 `probe_cache.py --run` 时已自动注入。**撞到 ModuleNotFoundError 一律先修路径，禁止把池中实现内联抄一份**
- **两支样板已进池（别再手写）**：定位技能根 `scripts/` 用 `sys.path.insert(0, str(P.find_skill_scripts()))`（池内判据：候选目录须真含 `probe_cache.py`；候选＝`MATH_MODEL_SKILL_SCRIPTS` → 本文件所在目录 → 已知安装位），**禁止再手写候选路径列表**；起步窗加密的 `t_out` 用 `P.ramp_t_out(t_end, t_fine_end, dt_fine, dt_coarse, dt_out=60.0)`（窗内逐 `dt_fine`、窗后只留 `dt_out` 交付行），**禁止再手写阶梯循环**——窗口数值（`t_fine_end` 等）属单题参数，放 `const.json` 后传参，不进池
- **进池判据（rule of two：同一口径出现第二次就提升，禁止再写副本）**——须同时满足：① 会被 ≥2 个小问/阶段调用；② 口径已固化（单位/坐标系/场景作用域明确，题目参数外置 `const.json`）；③ 纯函数优先（输入→输出、无副作用、不依赖某问私有中间产物）；④ 有对拍值或库函数交叉核对能证明"同一口径"；⑤ 是性能敏感热路径（慢副本代价 > import 代价）
- **判据的机械验证**：写完核心代码后跑 `python <技能根>/scripts/reuse_lint.py --scan --root <outputDir>` —— 它把函数规范化成骨架聚类，报出「同形实现出现在 ≥2 个文件」的组（含建议权威、是否已登记、是否跨小问）；扫出的组就是对「该进池」的客观候选，**后写份一律改 import**，口径不一致则在产物里写明差异并各自登记 `scope`
- **不进池（避免池变成垃圾场）**：一次性 EDA/画图/表格脚本（留本问阶段目录）；只服务单个小问的口径（留本问目录并在 manifest 标 `"scope":"q3"`）；口径仍在探索、还会改动者（**固化后再 promote**，提前进池会让下一个人复用到一个还在变的实现）；依赖某问私有数据路径/中间产物的胶水；一行的库函数包装（如 `np.clip`）
- **晋升阶梯（只升不降；新写任何核心前先自问"这是第几次需要它"）**：本问阶段目录 →（第二次需要）→ `pool/problem/<题>/` 并登记 manifest 的 `口径/单位/被复用/对拍值` →（去掉题目参数仍成立）→ `<技能根>/scripts/primitives.py`（走 `--selftest` 全绿 + 版本号递增）。**第 2 次需要某口径时不得再写新副本**（案例依据见仓库 `docs/prompt-audit-2026-09-11.md` §16）。
