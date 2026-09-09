# Vendored: diagram-design skill

- **上游**：https://github.com/cathrynlavery/diagram-design（MIT License，©2025 Cathryn Lavery）
- **上游 commit**：`2724fd2efd8c6737f6fa704fbf5da52d67375497`（2026-09-07，plugin 2.6.17）
- **本目录内容** = 上游仓库 `skills/diagram-design/` 全量原样拷贝 + `LICENSE` + `THIRD_PARTY_LICENSES.md`
- **修改**：无（全量拷贝，未裁剪未改动）
- **用途**：math-model 可视化/写作阶段画示意图（HTML→PNG），使用配方见 `docs/flowchart-drawing.md`（本 skill 的 docs/）

## 更新步骤（上游发版时）

1. 上游仓库 `git pull`，记录新 commit SHA
2. 整目录替换：
   ```bash
   rm -rf tools/diagram-design
   cp -r <上游>/skills/diagram-design tools/diagram-design
   cp <上游>/LICENSE <上游>/THIRD_PARTY_LICENSES.md tools/diagram-design/
   ```
3. 验证：`python3 tools/diagram-design/scripts/self_check.py <任一 example-*.html>` 通过
4. 更新本文件 SHA/日期后提交

## 许可要点（MIT 合规）

- `LICENSE`（含版权行）与 `THIRD_PARTY_LICENSES.md`（Tabler/Simple Icons/logos/Devicon 等）随副本保留
- 图标字体不打包（Google Fonts 走 CDN）；品牌图标仅文档性使用（见 THIRD_PARTY_LICENSES.md Trademarks 节）
