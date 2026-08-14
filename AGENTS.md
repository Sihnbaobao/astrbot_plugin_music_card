# 项目开发约定

本文件是给 AI 助手（opencode）看的规则，改代码前先读这里。

## 每次改动代码必须同步的 5 处

任何影响插件功能的修改（新增功能、修 bug、优化、改工具描述等）都必须：

1. **更新版本号**：`metadata.yaml` 里的 `version` 递增（patch/fix 加一位小数位，如 `1.1.0` -> `1.1.1`；新功能升 `1.2.0`）。
2. **更新 `changelog.md`**：在文件顶部新增该版本的条目，用 `## vX.X.X` 格式，中文描述改动。
3. **同步 `README.md`**：在"更新日志"一节顶部加上对应版本条目，格式为 `- **X.X.X** 改动描述`。
4. **同步插件源版本号**：修改 `D:\GithubProjects\astrbot-plugin-source\plugins.json` 中本插件记录的 `version` 为 `metadata.yaml` 的新版本号，并在该仓库单独 commit 后推送（`https://github.com/Sihnbaobao/astrbot-plugin-source`）。
5. **同步代码内版本号**：`main.py` 中 `@register(...)` 的版本号与 `metadata.yaml` 一致。

以上缺一不可，改完要一起 commit（插件源仓库单独 commit 并推送）。

## 只改文档不升版本

纯文档改动（README、changelog 修正、注释）不强制升版本，但若与已发布的版本内容不一致，仍应同步并提交。

## 提交规范

- 每次 commit 前运行 `git status` 和 `git diff` 检查改动范围。
- commit 信息用简短中文，格式参考：
  - `feat: ...`（新功能）
  - `fix: ...`（修 bug）
  - `chore: bump version to X.X.X`（仅升版本）
  - `docs: ...`（文档）
- 改完必须推送：`git push origin main`。

## 发布步骤（改完代码后）

1. 递增 `metadata.yaml` 版本号。
2. 更新 `changelog.md`。
3. 更新 `README.md`。
4. 同步插件源版本号（`astrbot-plugin-source\plugins.json`）并推送插件源仓库。
5. 全部一起 commit 并 push。

## 注意事项

- 修改 LLM 工具（`main.py` 里的 `@filter.llm_tool`）的 docstring 会影响 AI 调用行为，改完要提醒用户重启 AstrBot 才生效。
- 文件用 UTF-8、4 空格缩进，保持现有代码风格。
