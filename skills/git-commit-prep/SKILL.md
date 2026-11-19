---
name: git-commit-prep
description: Git 提交前准备流程。当用户说"提交前准备"、"清理临时脚本"、"git commit"等类似话语时触发。执行步骤：1) 运行 git status 查看变更，2) 仅删除本次修改中的临时脚本（不影响未变更的旧文件），3) 分析变更内容并提供符合 fix/feat 格式的中文 commit message
disable-model-invocation: true
---

## 执行步骤

### 1. 检查 Git 状态

```bash
git status
```

### 2. 仅清理本次修改中的临时脚本

**重要原则**：只删除本次 git status 显示为 **new file** 或 **modified** 的临时脚本，不清理历史遗留文件。

从 `git status` 输出中识别临时脚本（如 `check-*.js`、`test-*.js`），然后逐个删除：

```bash
# 仅删除 git status 中显示的临时脚本
rm scripts/具体文件名.js
```

### 3. 分析变更并生成 Commit Message

根据 `git status` 显示的修改文件，分析变更内容，生成符合规范的 commit message。

**格式规范**：
- 前缀：`fix:` 或 `feat:`
- 内容：简洁的中文描述，说明做了什么

**示例**：
```bash
fix: 同步E教研资源时过滤掉目录记录
feat: 添加学生积分排行榜功能
fix: 修复登录接口 Token 验证错误
```

## 输出格式

清理完成后，只输出一行 commit message 供用户直接使用：

```
fix: xxxxxxxx
```
或
```
feat: xxxxxxxx
```
