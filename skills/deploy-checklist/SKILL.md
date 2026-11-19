---
name: deploy-checklist
description: 项目部署检查清单。当用户说"部署清单"或询问"如何部署"时使用此技能，分析本次代码变更并生成包含以下5项的部署清单：1)是否需要数据库迁移(pnpm db:push) 2)是否需要执行脚本(新增/修改scripts/中的脚本，或字典表变更需要同步) 3)是否需要配置新环境变量(.env新增或修改) 4)是否需要部署前端(运行deploy脚本) 5)是否需要部署后端(restart screen server)
disable-model-invocation: true
---

# 部署检查清单

当用户说"部署清单"时，分析本次 git 变更并按以下格式输出：

```
## 部署清单

### 本次变更内容
[简要描述本次变更的文件和功能]

### 部署步骤

| 步骤 | 操作 | 说明 |
|------|------|------|
| 1 | [操作描述] | [详细说明] |
| ... | ... | ... |

### 不需要做的事 ✅
- ❌ **不需要** [xxx]
- ❌ **不需要** [xxx]
```

## 判断逻辑

### 1. 数据库迁移 (pnpm db:push)
检查 `prisma/schema.prisma` 或 `prisma/migrations/` 是否有变更。

### 2. 执行脚本
检查 `scripts/` 目录下是否有新增或修改的 `.js` 或 `.sh` 脚本。
如果有，需要在服务器上执行相应脚本。

### 3. 配置环境变量
对比 `.env.example` 的变更，确认是否需要新增或修改环境变量。
注意：敏感信息（API_KEY、SECRET等）不要写入 env.example。

### 4. 部署前端
检查 `/Users/czm/szkj/pad-admin-ui/front-end/` 目录下是否有变更。
如果有，需要运行前端 deploy 脚本。

### 5. 部署后端
检查 `src/` 目录下是否有代码变更（Controller、Service、Route 等）。
如果有，需要重启后端服务：`screen -r server` → `Ctrl+C` → `pnpm start`
