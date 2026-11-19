---
name: macos-app-dev
description: macOS App 开发技术指导：从工程结构、代码签名、权限声明上根治 TCC 反复弹窗。个人/自有项目全量执行；公司/团队项目只讲解不动配置。仅手动调用，不自动触发——用户点名「macos-app-dev」或要求开发 macOS 桌面应用并明确要用这套规范时才载入。
disable-model-invocation: true
---

# macOS App 开发防权限弹窗规范

目标：开发 macOS 桌面工具时，从项目初始化阶段就按本规范搭建工程，让敏感权限**只需授权一次**，以后改代码、重编译都不再弹窗。

## 0. 适用范围（先判定，再执行）

1. **个人/自有项目**：按本规范全量执行，工程结构、签名、沙盒、权限配置都直接改。
2. **公司/团队项目**：默认只讲解、不动任何配置；确需改签名、Bundle ID、entitlements 时，先逐项列出改动并征得用户确认，冲突时以公司现有签名/发布规范为准。
3. 用户明确说「本项目不用这套规范」时，直接跳过本技能。

## 1. 原理（为什么反复弹窗）

macOS 隐私保护（TCC）认的是**代码签名 + 固定 Bundle ID**，不看代码内容：

- 无签名 / Ad-hoc 签名 → 每次重新编译哈希都变 → 系统当成全新程序 → 辅助功能、麦克风等权限反复失效、反复弹窗。
- 绑定正式开发者签名（固定 Team ID + Bundle ID）→ 系统认人 → **授权一次永久生效**。

## 2. 项目初始化硬性规范（逐条执行，不得跳过）

1. **工程结构**：必须生成标准 `.app` 应用包（完整 Xcode 工程，或带完整 `Info.plist` 的打包脚本），禁止让用户直接运行无签名的单文件脚本或裸二进制。
2. **Bundle ID**：唯一且固定，形如 `com.<用户名>.<项目名>`；不留空、不用冲突占位符。
3. **签名**：正式代码签名（Apple Development），固定 Team，禁止 Ad-hoc / Sign to Run Locally。本机开发者账号、Team ID、证书的对照关系见用户级 `~/.dsh/AGENTS.md` 第 23 节，不要在本技能里重复记录。
4. **沙盒**：需要全局快捷键、模拟按键、跨应用操作的工具，必须关闭 App Sandbox（entitlements 中设为 false），否则会拦截模拟粘贴等操作。
5. **权限声明**：`Info.plist` 预先写好全部会用到的权限用途描述（如 `NSMicrophoneUsageDescription`、`NSAppleEventsUsageDescription`），不要等运行时报错再补。
6. **能不申请的权限不申请**：
   - 全局快捷键优先用 `RegisterEventHotKey`（系统公开 API，**不需要**「输入监控」权限）。
   - 可接受手动粘贴的场景：文本放剪贴板 + 提示音，**完全免「辅助功能」权限**。
   - 要自动上屏才申请「辅助功能」，签名固定后同样只需授权一次。
7. **旧幽灵记录清理**：系统设置 → 隐私与安全性 → 辅助功能 / 输入监控，删除之前无签名测试留下的同名旧记录，再重新授权一次。

## 3. 验收标准（全部满足才算配置完成）

1. `codesign -dv --verbose=4 <App>.app`：Authority 显示开发者证书，`TeamIdentifier` 不是 `not set`。
2. 授权一次后，**改一行代码重新编译运行，不再弹任何权限请求**，功能直接生效。
3. 权限相关功能（快捷键、录音、粘贴）真实操作验证通过；测试要求另见 `~/.dsh/AGENTS.md` 第 24 节（XCTest 实测）。

## 4. 给其他 AI 工具的提示词模板

用户在 Cursor / Claude Code 等非 DSH 工具里开发时，把下面模板原样给出：

> 我正在开发一个 macOS 桌面工具，有自己的 Apple 开发者账号。为避免每次重新编译都触发 TCC 反复弹窗，请严格遵守：① 生成标准 .app 工程结构（或完整 Xcode 工程），配置唯一固定的 Bundle Identifier（com.myname.<项目名>）；② 构建配置启用正式代码签名（Apple Development），保留 DEVELOPMENT_TEAM 占位符引导我填自己的 Team ID，禁止 Ad-hoc 签名；③ entitlements 关闭 App Sandbox；④ Info.plist 预写所需权限用途描述；⑤ 全局快捷键优先用 RegisterEventHotKey，能不申请的敏感权限不申请。

## 5. 与既有规则的关系

- `~/.dsh/AGENTS.md` 第 23 节：本机签名账号与描述文件的环境事实（Team ID、capability 机制）——环境问题查那里。
- `~/.dsh/AGENTS.md` 第 24 节：App 开发的 XCTest 测试要求——测试问题按那里执行。
- 本技能只管「工程结构 + 签名 + 权限声明」这套初始化规范，不重复上述内容。
