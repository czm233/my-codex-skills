---
name: dsh-plugin-sync
description: 在公司 MacBook 与家里 Windows 之间同步自研 DSH 插件：任一台做好的插件，另一台立刻接上可用。用户说「同步插件」「插件上线」「插件接上」时使用。只同步插件代码与安装登记；用户级配置、画布、角色库、密钥一律不搬；插件仓有未提交改动时直接停止交用户处理。
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

# DSH 插件双机同步

唯一真相：公开仓 `github.com/czm233/my-dsharness-plugin` 的 main。**push 即同步意图**——推上去的内容就是要另一台接上的内容；没推的改动属于本机。**方向跟人走，不跟机器走**：两台都可能改插件、都可能上线、都可能接上。

边界：只动插件仓和 DSH profile 的插件登记表。`cordis.patch.yml`、API keys、画布、角色库、workflow-lite 图、rules 一律不碰、不读、不迁移。

标准位置：插件仓 `~/githubProject/my-dsharness-plugin`（Mac 与 Windows 同构）；DSH profile 为 `~/.dsh/profiles/` 下带 `package.json` 的目录。

## 「插件上线」（任一台：把本地状态推上去）

1. `git -C <插件仓> pull --rebase --autostash`。
2. 工作区脏（`git status --porcelain` 非空）→ **立即停止整个同步**，列出脏文件清单，请用户手动处理（提交或丢弃）后再跑一次。不要代提交。
3. 一致性速查（只提醒，不阻塞）：本轮改动涉及版本号的插件，`package.json` 版本是否已升、根 `index.json` 是否登记了新版本和 commit——缺了按该仓库 AGENTS.md §4/§5 提醒用户补齐。
4. `git push`。用户说「插件上线」即授权推送；本地不领先就说明已是最新。

## 「插件接上」（任一台：把远端状态接上）

1. 插件仓不存在 → 转第 4 节首次接上。
2. `git pull --rebase --autostash`；工作区脏 → 同「插件上线」第 2 步，停止交用户。
3. 扫描插件仓根下含 `package.json` 的插件目录，与 profile `package.json` 比对：缺的 `@local/*` 依赖补 `link:` 条目（本机绝对路径、正斜杠），`dsh.profile.bundles` 缺的补登记；已存在的不动。
4. `pnpm install`——优先用 DSH 内置 runtime（`~/.dsh/dsh-runtimes/*/dependencies/` 下的 node 与 `pnpm/bin/pnpm.cjs`）；装完逐个验证 `node_modules/@local/*` 链接目标存在。
5. 对比 pull 前后的变更，按热更新规则提示生效方式：只动 `client.js`/`locale`/`icon` → 重载界面即可；动了 `index.js`/`host.js`/`cordis.patch.yml`/`package.json` → 需要 remove+install 重装（本会话有 plugin_manager 工具就代做，没有就提示在 GUI 里重装该插件）。

## 「同步插件」

= 先接上、再上线，连做一遍。

## 首次接上（任一台第一次）

前置：Git 已装；DSH 已安装且启动过一次（profile 已生成）。

1. `git clone https://github.com/czm233/my-dsharness-plugin` 到标准位置。
2. 执行「插件接上」第 3-4 步（全量登记 + pnpm install）。
3. 检查 profile `cordis.patch.yml` 的 `plugin-market.indexes` 是否含 `https://raw.githubusercontent.com/czm233/my-dsharness-plugin/main/index.json`；没有就征得用户同意后加上——这是插件市场能看到这批插件的唯一途径，属「插件可用」的最小配置。加完提醒重启 DSH。
4. 告知用户：纯使用场景也可以不走本地 link，直接在 DSH 插件市场里点安装；link 方式的好处是后续每次同步只差一次 pull + install。

## 故障处理

- pull --rebase 冲突：停止，报告冲突文件，交用户裁决。
- pnpm install 失败：带上报错尾部报告，不静默重试。
- 软链接目标不存在：逐个列出，提示重跑登记 + install（不要手 ln，登记表才是源头）。
