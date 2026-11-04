# Bark Notifications

同一插件源码目录提供 Codex 和 DeepSeek Harness 两个入口。设备上的文件是安装产物，不是独立维护的源码。所有修改先在仓库完成，再发布新版本并由客户端更新。

## DeepSeek Harness（macOS）

0.4.0 起同一 DSH bundle 在 macOS 上启用两条通知路径：

- **审批等待**：旁听 `approval/request` 事件瀑布——只发通知后原样 `next()` 透传，不回答、不拦截，任何失败都被吞掉，不影响审批主流程。桌面横幅（osascript）+ Bark 推送（`level=timeSensitive`）；审批处理后补发一条结果通知。
- **回合结束**：与 Windows 相同的 turn-stopping Hook，经 `POST https://api.day.app/push` 发送。

凭证：Bark device key 从登录钥匙串读取（service `codex-bark-notifications`、account `codex`），不经命令参数、仓库、日志或聊天；缺失时状态记为 `credential_unavailable`。本地配置 `~/Library/Application Support/DSHBark/settings.json` 仅存非敏感项：`machine_label`、`sound`、`desktop`（false 关桌面横幅）、`notify_answered`（false 关结果通知）。

### 服务器地址与钥匙串条目（0.4.2 起可配置）

默认值就是历史行为，什么都不配时请求仍发往 `https://api.day.app/push`：

| 配置项 | settings.json 字段 | 默认值 | 说明 |
| --- | --- | --- | --- |
| baseUrl | `bark_base_url` | `https://api.day.app` | 只写服务器根地址，**不要带 `/push`**；带了也会被去掉 |
| keychainService | `bark_keychain_service` | `codex-bark-notifications` | 钥匙串 service 名 |
| keychainAccount | `bark_keychain_account` | `codex` | 钥匙串 account 名 |

优先级：**DSH 插件配置 > settings.json > 默认值**。插件配置来自 DSH 的 `apply(ctx, config)`，写成 `bark: { baseUrl, keychainService, keychainAccount }`（顶层同名键也接受）。理由：插件配置是应用级、显式、临时生效的覆盖；settings.json 是本机偏好。改 settings.json 不用重启 DSH，下一次推送即生效；改插件配置需要重启 DSH。

无效值（非 http/https、带账号密码/查询串、空串）会被忽略并回落到下一级，不会静默发到别处。`/push` 拼接会去掉末尾斜杠，不会出现 `//push` 或 `/push/push`。

自建服务器示例（地址与 key 均需换成自己的，key 只进钥匙串、不进本文件）：

```json
{"bark_base_url":"http://10.100.0.2:30137","bark_keychain_service":"codex-bark-notifications-selfhosted"}
```

切到自建服务器后必须换成该服务器注册的 device_key，官方 key 在自建服务器上无效（返回 400）。两个 key 可以并存：用不同的 `bark_keychain_service` 分开存。

自检（只输出地址、来源与 key 是否存在，不输出 key）：

```sh
node -e "import('dsh/index.mjs').then(async m=>console.log(m.formatBarkConfig(await m.inspectBarkConfig())))"
```

Windows 入口（`dsh/send.ps1`）目前仍只支持官方地址 `https://api.day.app/push`。

Codex 入口（`skills/bark-notifications/bin/bark-task-complete`）读的是 `~/.codex/bark-notifications.json`，同样支持 `bark_base_url`、`bark_keychain_service`、`bark_keychain_account`，缺省行为不变。

## DeepSeek Harness（Windows）

本目录的 `package.json` 声明 DSH bundle，`cordis.patch.yml` 按包名加载 `dsh/index.mjs`。通过 Harness「插件」页面安装发布版本；不要把源码复制到 `.dsh/plugins`，不要手工编辑桌面 profile 的依赖清单。

更新仍通过插件市场选择新版本安装。Git 来源固定到提交，更新版本不依赖可变的本地文件。首次迁移前备份 profile；确认新包可加载后移除旧的本地 Bark patch，避免双重通知。其他插件与配置必须保留。

### 本地配置与凭证

这些文件独立于插件安装目录，更新时保持不变：

- `%LOCALAPPDATA%\DSHBark\settings.json`：`machine_label`、`sound`。
- `%LOCALAPPDATA%\DSHBark\device-key.dpapi`：Windows 当前用户 DPAPI 加密凭证；不能复制给另一 Windows 用户使用。
- 同目录的 `dedup` 与 `diagnostics.jsonl`：去重记录和不包含通知内容的诊断。

配置示例（仅示例值）：

```json
{"machine_label":"My Windows","sound":"bell_quiet"}
```

标题为会话标题加机器标签，正文为当前回复最多 30 个字符的预览。机器标签缺省使用 Windows 计算机名；铃声缺省 `bell_quiet`。不会读取会话历史；标题或预览缺失时跳过；发送失败不重试、不影响任务。

首次配置凭证应通过安全输入在目标 Windows 用户上下文中使用 DPAPI 加密，并限制文件 ACL；不要将明文放进命令参数、仓库、日志或聊天。现有设备迁移无需重新读取或搬运凭证。

### 验证

`npm test` 验证去重、子智能体排除、事件注册和格式；Windows 额外验证 PowerShell 的中文输入。真实验收通过 Harness 会话完成事件触发，不能直接运行发送脚本代替 Hook 验证。HTTP 成功只表示服务接受推送，手机横幅需要用户确认。

## Codex（macOS）

继续使用同目录 `.codex-plugin`、`hooks` 和 `skills` 的现有插件入口，参见 `skills/bark-notifications/references/codex-hook-setup.md`。凭证保存在钥匙串，设备配置保存在插件目录之外。

## 统一发布与更新

源码唯一来源：https://github.com/czm233/my-codex-skills 。修改插件时同步提高 `package.json`、`.codex-plugin/plugin.json` 和根目录 `marketplace.json` 中 Bark 条目的版本号。推送主分支后，GitHub Actions 验证 Windows/macOS，再生成固定提交的 Harness 市场目录；检查工作流成功后通知设备更新。

Harness：启用「自定义插件市场」，在「发现」添加索引：

`https://raw.githubusercontent.com/czm233/my-codex-skills/main/dsh-marketplace.json`

刷新索引，选择 Bark Notifications 的新版本安装。当前 Harness 对第三方包可能要求先卸载再安装新版；卸载插件不会删除本插件放在 `%LOCALAPPDATA%\DSHBark` 的设置与凭证。需要重启时按客户端提示操作。首次安装仍需完成本地凭证配置；更新不会改变已有设置。

Codex：从同一 GitHub 仓库刷新市场并安装新版：

```sh
codex plugin marketplace add czm233/my-codex-skills
codex plugin marketplace upgrade my-codex-skills
codex plugin add bark-notifications@my-codex-skills
```

修改公共通知规则时必须覆盖两个运行时的测试；两个入口在同一个版本内发布，不能在目标电脑单独改安装产物。版本更新由各客户端执行，不等于 Git push 后所有设备立即自动更新。
