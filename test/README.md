# math-model 冒烟测试夹具（test/）

极简数模题 + 内置数据，用于**快速验证 v3 薄壳流水线有效性**（逐问串行 10 阶段 + 跨问复核/写作/终审 + 3 门禁 + PDF 编译）。

## 内容

| 路径 | 说明 |
|---|---|
| `data/population.csv` | 测试数据：2015–2024 某县级市常住人口（万人），近似线性增长 |
| `intermediates/00-problem.json` | Stage 1 落盘产物（题面/数据画像/论文规则/审题 JSON）——流水线**唯一**题源，勿删 |

## 题目

- 问题 1：建立模型预测 2025 年常住人口，说明模型选取依据
- 问题 2：给出预测的 95% 置信区间，讨论适用前提与局限

预期答案：一元线性回归，2025 ≈ 13.1–13.2 万人，R² ≈ 0.99。

## 运行方式（quick 模式）

```json
{
  "outputDir": "<本仓库>/test",
  "templateDir": "<本仓库>/skills/math-model",
  "mode": "quick",
  "innovationStrictness": "standard",
  "resume": false
}
```

## 验收点

- `intermediates/state.json` 存在，13 阶段全部 `PASS`
- `intermediates/q1/`、`q2/` 下 10 个阶段产物齐全（01-literature … 10-completed）
- `intermediates/13-final/final-paper.pdf` 编译成功（xelatex）
- 摘要数字能在正文/代码中找到出处（终审硬门禁）
- 中断后可 `resume: true` 续跑

> 说明：`test/intermediates/` 下除 `00-problem.json` 外的全部运行产物被 `.gitignore` 忽略，重跑前可整目录删除。
