---
name: hotfix-worktree
description: |
  基于 git worktree 的热修复工作流管理。当用户说"创建热修复"、"hotfix"、"创建worktree"、"清理热修复"、"推送热修复"、"启动热修复"、"hotfix create"、"hotfix start"、"hotfix push"、"hotfix remove"等意图时触发。支持4个操作：create（创建热修复环境）、start（启动热修复服务）、push（推送修复到远程main）、remove（清理热修复环境）。
disable-model-invocation: true
---

# Hotfix Worktree 工作流

基于 `git worktree` 实现前后端热修复的全流程管理，让你在主分支有未提交功能代码时，也能安全地做 bug 修复。

## 解析用户意图

根据用户输入判断要执行的操作：

| 用户输入 | 操作 | 说明 |
|---------|------|------|
| "创建热修复 xxx" / "hotfix create xxx" | create | 创建热修复环境 |
| "启动热修复" / "hotfix start" | start | 启动热修复服务 |
| "推送热修复" / "hotfix push" | push | 推送修复到远程 main |
| "清理热修复" / "hotfix remove" | remove | 清理热修复环境 |

如果用户只说了"hotfix"或"创建热修复"但没有指定名称，**必须询问热修复名称**（用于分支名 `fix/<名称>`）。

---

## 目录结构

```
~/projects/
├── agents-e539fb347b/                  # 后端主 worktree (main, 日常开发)
│   └── .env                            # PORT=3000
└── agents-e539fb347b-hotfix/           # 后端热修复 worktree
    └── .env                            # PORT=3002, CORS_ORIGIN=http://localhost:3102

~/szkj/pad-admin-ui/
├── .git/
├── front-end/                          # 前端主 worktree (main, 日常开发)
│   └── vite.config.js                  # port: 3100, proxy → 3000
└── front-end-hotfix/                   # 前端热修复 worktree
    └── front-end/                      # 项目代码（仓库结构导致多一层）
        └── vite.config.js              # port: 3102, proxy → 3002
```

## 端口分配

| 服务     | 主 worktree | 热修复 worktree | 说明 |
|----------|-------------|-----------------|------|
| 后端     | 3000        | 3002            | .env PORT 控制 |
| 前端     | 3100        | 3102            | vite.config.js 中修改 |
| CORS     | localhost:3100 | localhost:3102 | .env CORS_ORIGIN 控制 |
| MySQL    | 3306 (共用) | 3306 (共用)     | 共用安全 |
| Redis    | 6379 (共用) | 6379 (共用)     | 共用安全 |

## ⚠️ 限制

- **仅适用于不动数据库 schema 的修复**：两个 worktree 共用 MySQL，schema 变更会冲突
- **同时只支持一个 hotfix worktree**：避免端口和目录管理复杂化
- **前后端分支名一致**：都叫 `fix/<名称>`，方便关联和清理

---

## 操作 1: create — 创建热修复环境

**参数**: `<名称>` — 用于分支名 `fix/<名称>`

### 前置检查

```bash
# 检查是否已存在 hotfix worktree（同时只支持一个）
ls -d /Users/czm/szkj/pad-admin-api/back-end-hotfix 2>/dev/null && echo "HOTFIX_EXISTS" || echo "OK"
ls -d /Users/czm/szkj/pad-admin-ui/front-end-hotfix 2>/dev/null && echo "HOTFIX_EXISTS" || echo "OK"
```

如果已存在，提示用户先运行 `remove` 清理旧的热修复环境。

### 后端 worktree

```bash
# 1. 进入后端主仓库
cd /Users/czm/szkj/pad-admin-api/back-end

# 2. 拉取最新远程代码
git fetch origin

# 3. 创建 worktree，基于 origin/main 创建新分支
git worktree add ../agents-e539fb347b-hotfix -b fix/<名称> origin/main

# 4. 复制 .env 到 hotfix worktree
cp .env ../agents-e539fb347b-hotfix/.env

# 5. 修改 hotfix 的 .env: PORT=3002, CORS_ORIGIN=http://localhost:3102
# 使用 Edit 工具修改 /Users/czm/szkj/pad-admin-api/back-end-hotfix/.env 中的：
#   - PORT=3000 → PORT=3002
#   - CORS_ORIGIN=... → CORS_ORIGIN=http://localhost:3102

# 6. 安装依赖和生成 Prisma Client
cd /Users/czm/szkj/pad-admin-api/back-end-hotfix
pnpm install && pnpm run db:generate
```

### 前端 worktree

```bash
# 1. 进入前端主仓库
cd /Users/czm/szkj/pad-admin-ui

# 2. 拉取最新远程代码
git fetch origin

# 3. 创建 worktree，使用相同的分支名
git worktree add front-end-hotfix -b fix/<名称> origin/main

# 4. 安装依赖
cd /Users/czm/szkj/pad-admin-ui/front-end-hotfix/front-end
pnpm install
```

### 修改前端 vite.config.js

读取 `/Users/czm/szkj/pad-admin-ui/front-end-hotfix/front-end/vite.config.js`，修改：
- `server.port`: 改为 `3102`
- `server.proxy` 的 target: 改为 `http://localhost:3002`

### 创建完成后输出

```
✅ 热修复环境创建成功！

分支: fix/<名称>
后端目录: /Users/czm/szkj/pad-admin-api/back-end-hotfix (PORT=3002)
前端目录: /Users/czm/szkj/pad-admin-ui/front-end-hotfix/front-end (PORT=3102)

下一步:
  1. 运行 "启动热修复" 或 "hotfix start" 启动服务
  2. 在 hotfix 目录中修改代码
  3. 修复完成后运行 "推送热修复" 或 "hotfix push"
```

---

## 操作 2: start — 启动热修复服务

### 前置检查

```bash
# 确认 hotfix worktree 存在
ls -d /Users/czm/szkj/pad-admin-api/back-end-hotfix 2>/dev/null || echo "NOT_FOUND"
```

如果不存在，提示用户先运行 `create` 创建。

### 启动后端

```bash
cd /Users/czm/szkj/pad-admin-api/back-end-hotfix
PORT=3002 nohup npx nodemon src/app.js > /tmp/hotfix-backend.log 2>&1 &
echo "后端 PID: $!"
```

等待几秒后验证：

```bash
sleep 3
curl -s http://localhost:3002/health | head -c 200
```

### 启动前端

```bash
cd /Users/czm/szkj/pad-admin-ui/front-end-hotfix/front-end
nohup npx vite --port 3102 > /tmp/hotfix-frontend.log 2>&1 &
echo "前端 PID: $!"
```

### 启动完成后输出

```
✅ 热修复服务已启动！

后端: http://localhost:3002 (日志: /tmp/hotfix-backend.log)
前端: http://localhost:3102 (日志: /tmp/hotfix-frontend.log)

查看日志:
  tail -f /tmp/hotfix-backend.log
  tail -f /tmp/hotfix-frontend.log
```

---

## 操作 3: push — 推送修复到远程 main

**⚠️ 严格流程，不可跳步！**

### 步骤 1: 检查并提交修复

```bash
# 后端
cd /Users/czm/szkj/pad-admin-api/back-end-hotfix
git status
git diff
```

如果有未提交的修改，按正常 commit 流程提交（遵循 AGENTS.md 的 git 规范）。

### 步骤 2: 拉取最新远程 main 并 rebase

```bash
cd /Users/czm/szkj/pad-admin-api/back-end-hotfix
git pull --rebase origin main
```

#### 有冲突 → 立即停止

```
⚠️ Rebase 过程中出现冲突！

冲突文件:
  [列出冲突文件]

AI 不得自行解决冲突（同事的代码逻辑 AI 不了解上下文）。
请手动解决冲突后执行:
  cd /Users/czm/szkj/pad-admin-api/back-end-hotfix
  # 解决冲突文件...
  git add <冲突文件>
  git rebase --continue

解决后再次运行 "推送热修复" 继续流程。
```

#### 无冲突 → 必须重新自测

**rebase 后代码基础变了，可能有隐性影响，必须自测！**

1. 重启 hotfix 后端服务
2. 用 api-probe 或 curl 验证修复的接口/功能
3. 确认无误后才能继续

### 步骤 3: 自测通过后推送

```bash
cd /Users/czm/szkj/pad-admin-api/back-end-hotfix
git push origin HEAD:main
```

### 前端（如有改动）

```bash
cd /Users/czm/szkj/pad-admin-ui/front-end-hotfix

# ⚠️ 推送前先还原 vite.config.js 的端口改动（本地配置不提交）
git checkout -- front-end/vite.config.js

# 提交修复
git add <files>
git commit -m "fix: xxx"

# rebase
git pull --rebase origin main
# 有冲突 → 人工介入，无冲突 → 自测后推送

git push origin HEAD:main
```

### 推送完成后输出

```
✅ 修复已推送到远程 main！

后端提交: [commit hash] [commit message]
前端提交: [commit hash] [commit message]（如有）

下一步:
  1. 通知运维/CI 部署最新代码
  2. 运行 "清理热修复" 或 "hotfix remove" 清理环境
```

---

## 操作 4: remove — 清理热修复环境

### 步骤 1: 停止服务

```bash
# 停止端口 3002（后端）和 3102（前端）的进程
lsof -ti:3002 | xargs kill -9 2>/dev/null
lsof -ti:3102 | xargs kill -9 2>/dev/null
```

### 步骤 2: 获取分支名

```bash
# 读取 hotfix worktree 当前所在分支
cd /Users/czm/szkj/pad-admin-api/back-end-hotfix 2>/dev/null && git branch --show-current
```

### 步骤 3: 清理后端 worktree

```bash
cd /Users/czm/szkj/pad-admin-api/back-end
git worktree remove ../agents-e539fb347b-hotfix --force
git branch -d fix/<名称>
```

如果 `git branch -d` 失败（分支未合并），提示用户确认是否强制删除（`-D`）。

### 步骤 4: 清理前端 worktree

```bash
cd /Users/czm/szkj/pad-admin-ui
git worktree remove front-end-hotfix --force
git branch -d fix/<名称>
```

同样，如果分支未合并，提示确认。

### 步骤 5: 验证清理

```bash
# 确认 worktree 已移除
cd /Users/czm/szkj/pad-admin-api/back-end && git worktree list
cd /Users/czm/szkj/pad-admin-ui && git worktree list
```

### 清理完成后输出

```
✅ 热修复环境已清理！

已删除:
  - 后端 worktree: agents-e539fb347b-hotfix
  - 前端 worktree: front-end-hotfix
  - 分支: fix/<名称>

主 worktree 代码和配置未受影响。
```

---

## Git 流程示意

```
创建 worktree 时:
  origin/main:  A ─── B ─── C
                              └── hotfix worktree 基于 C 创建

开发修复期间，别人可能推了代码:
  origin/main:  A ─── B ─── C ─── E (别人的提交)

推送前 pull --rebase:
  hotfix:       C ─── D (fix)
                          ↓ rebase onto E
  hotfix:       C ─── E ─── D' (fix, rebased)

push HEAD:main:
  origin/main:  A ─── B ─── C ─── E ─── D' (修复已上线)

本地 main (不受影响):
  本地 main:    C + 未提交的功能开发...
                └── 功能完成后 pull --rebase 合入 E + D'
```
