# Codex Stop Hook 配置指南

本文记录如何在任意 macOS 电脑上安装用户级 `bark-notifications` 插件。插件启用并信任后，每次 Codex 用户可见主线程结束一个回合时发送一次 Bark 通知：标题为本机机器标签，正文为当前 Session 的用户可见标题。同一个 `session_id + turn_id` 只发送一次，Codex Desktop 为界面功能启动的内部临时 turn 不发送。插件停用或卸载后，插件 Hook 不再加载。

## 先理解组成部分

插件中包含三条可执行命令和一个生命周期 Hook：

- `hooks/hooks.json`：插件自带的用户级 `Stop` Hook，不修改 `~/.codex/hooks.json`。
- `bin/bark-stop-hook`：接收插件的 `Stop` 事件；存在 `CODEX_THREAD_ID` 时先确认事件 `session_id` 与当前可见线程一致，不一致的内部临时 turn 直接跳过；随后去重，再调用发送器。未提供 `CODEX_THREAD_ID` 的 Codex 表面保持原有按事件会话通知的兼容行为。
- `bin/bark-task-complete`：解析本机机器标签，从 macOS 钥匙串读取 Bark Device Key，通过 Bark `/push` 接口发送机器标签和经过清洗的 Session 标题。
- `bin/bark-configure-machine`：写入或显示本机非敏感机器标签，不读取或处理 Bark Key。

插件 Hook 通过 `${PLUGIN_ROOT}` 调用 Skill 内脚本。不要手动编辑 `~/.codex/hooks.json`，也不要在 `~/.codex/bin` 再复制一份 Bark 发送脚本。

## 安装用户级插件

在目标电脑的终端中，将包含仓库 `.agents/plugins/marketplace.json` 的仓库根目录加入本地插件市场，然后安装插件。下面的路径只是示例；请替换为目标电脑上的实际仓库路径：

```bash
REPO_ROOT="/path/to/my-codex-skills"
codex plugin marketplace add "$REPO_ROOT"
codex plugin add bark-notifications@my-codex-skills
```

`codex plugin add` 默认安装到当前用户作用域。不要把插件目录复制到 `~/.codex/skills`，也不要使用 `$plugin-creator` 代替安装命令；`plugin-creator` 只用于开发或校验插件目录。

插件安装完成后，确认插件已启用并通过 Hook 信任审核。插件缓存目录由 Codex 管理，不要把缓存绝对路径写进配置。

```text
插件缓存根目录/skills/bark-notifications/SKILL.md
插件缓存根目录/hooks/hooks.json
```

如果本机还残留旧的 Bark Skill 或用户级 Bark Hook，应先按迁移清单精确删除旧项；不要覆盖其他 Hook。

完成迁移后必须重启 Codex Desktop，或结束并重新启动对应的 Codex CLI/app-server 会话。Codex 会在会话启动时加载 Hook；已经运行的旧会话可能仍在内存中保留旧 `hooks.json`，即使磁盘上的旧文件已经删除，也会继续尝试执行旧路径并报“文件不存在”。重启后用 `/hooks` 确认 Stop Hook 的来源显示为 `bark-notifications@my-codex-skills`，命令路径包含 `${PLUGIN_ROOT}`；不要为了消除旧报错重新创建旧用户级 Hook。

## 在本机保存 Bark Key

Device Key 只保存到 macOS 钥匙串，不能写入仓库、`AGENTS.md`、`hooks.json`、脚本参数或聊天记录。

在目标电脑的本地终端执行下面的命令，并在提示时粘贴 Key。Key 不会出现在命令历史中：

```bash
read -r -s BARK_DEVICE_KEY
printf '\n'
/usr/bin/security add-generic-password \
  -U \
  -a codex \
  -s codex-bark-notifications \
  -w "$BARK_DEVICE_KEY"
unset BARK_DEVICE_KEY
```

脚本读取的固定钥匙串项目是：

```text
service: codex-bark-notifications
account: codex
```

不要用 `security find-generic-password -w` 把 Key 打印到终端或日志中。

## 配置本机机器标签

机器标签是每台电脑独立的非敏感配置，不属于 Skill 源码，也不能提交到仓库。它用于让 iPhone 和 Apple Watch 区分相同 Bark Key 发来的通知。

### 配置优先级

发送器按以下顺序解析机器标签：

1. 环境变量 `CODEX_BARK_MACHINE_LABEL`（适合企业批量部署或临时覆盖）。
2. `${CODEX_HOME:-$HOME/.codex}/bark-notifications.json` 中的 `machine_label`。
3. macOS `ComputerName`。
4. `hostname -s`。
5. `Mac`。

正常部署应使用本机 JSON 配置，不要依赖设备型号列表，也不要修改 Skill 源码。配置文件格式为：

```json
{
  "version": 1,
  "machine_label": "<用户确认的短标签>"
}
```

机器标签应控制在 24 个字符以内，避免换行和控制字符。安装 Agent 应先读取当前 `ComputerName` 作为建议值，再让用户确认或改成更短的标签；不要把未确认的真实电脑名称写入仓库。

使用 Skill 自带命令写入配置：

```bash
PLUGIN_ROOT="<插件安装根目录>"
SKILL_HOME="$PLUGIN_ROOT/skills/bark-notifications"
"$SKILL_HOME/bin/bark-configure-machine" --machine-label "<用户确认的短标签>"
"$SKILL_HOME/bin/bark-configure-machine" --show
```

如果已有配置，命令会拒绝静默覆盖不同标签；用户明确要求更换时才追加 `--force`。配置文件权限由命令设置为仅当前用户可读写。

通知标题使用机器标签，正文使用 Session 标题。机器标签同时用于 Bark 分组：

```text
MacBook Air
skill维护-bark-notifications
```

通知分组会包含机器标签，以便在 Bark 历史记录中按电脑区分。Session 标题只读取 `thread.name` 元数据，不读取对话正文；如果 Thread 尚未命名或读取失败，正文回退为“本轮回复已结束”。

## 插件 Hook 生命周期

不需要合并或编辑用户级 `hooks.json`。Codex 从已启用插件中加载 `hooks/hooks.json`，命令使用 `${PLUGIN_ROOT}` 定位插件内脚本。插件 Hook 与用户级、项目级 Hook 共同加载；如果另一层仍配置旧 Bark Hook，会造成重复通知，因此迁移时要删除旧 Bark Hook。

插件停用或卸载后，Codex 不再加载该插件的 Hook；这不会删除用户主动配置的其他 Hook，也不会删除 Keychain 中的 Bark Key 或机器标签配置。

## 审核并信任 Hook

非托管命令 Hook 需要人工审核。启动或重新加载 Codex 后：

1. 在 Codex CLI 执行 `/hooks`。
2. 找到新增或变更的 Bark `Stop` Hook。
3. 审核命令路径与脚本内容，确认它只读取钥匙串和 Thread 标题元数据，并向 Bark 发送机器标签与 Session 标题。
4. 信任该 Hook。

Hook 定义或脚本发生变化后，可能需要重新审核；不要使用绕过信任的危险选项作为长期配置。

## Dry-run 验证

先只验证发送器，不访问钥匙串或 Bark：

```bash
PLUGIN_ROOT="<插件安装根目录>"
printf '%s' 'Codex' | \
  "/usr/bin/python3" "$PLUGIN_ROOT/skills/bark-notifications/bin/bark-task-complete" turn_stopped --dry-run
```

预期输出类似：

```text
status=dry-run event=turn_stopped sent=false
```

再验证 Stop Hook 的去重路径。下面的测试使用临时状态目录，不发送真实通知：

```bash
TEST_STATE_DIR="$(mktemp -d)"
printf '%s' '{"hook_event_name":"Stop","session_id":"dry-run-session","turn_id":"dry-run-turn","stop_hook_active":false}' | \
  CODEX_THREAD_ID="dry-run-session" \
  CODEX_BARK_HOOK_DRY_RUN=1 \
  PLUGIN_DATA="$TEST_STATE_DIR/plugin-data" \
  CODEX_BARK_HOOK_STATE_DIR="$TEST_STATE_DIR" \
  /usr/bin/python3 "$PLUGIN_ROOT/skills/bark-notifications/bin/bark-stop-hook"
```

预期 Hook 输出为 `{}`，并且临时目录中只出现一个去重文件。相同 `session_id + turn_id` 再运行一次，不应新增文件。

再用一个不同的事件会话验证内部 turn 过滤：

```bash
printf '%s' '{"hook_event_name":"Stop","session_id":"internal-session","turn_id":"internal-turn","stop_hook_active":false}' | \
  CODEX_THREAD_ID="dry-run-session" \
  CODEX_BARK_HOOK_DRY_RUN=1 \
  CODEX_BARK_HOOK_STATE_DIR="$TEST_STATE_DIR" \
  /usr/bin/python3 "$PLUGIN_ROOT/skills/bark-notifications/bin/bark-stop-hook"
```

预期仍输出 `{}`，临时目录中的去重文件数量不变，表示内部临时 turn 没有进入通知链路。测试兼容回退时，可通过 `env -u CODEX_THREAD_ID` 执行原有 Dry-run；此时有效 Stop 事件仍按 `session_id + turn_id` 去重和通知。

## 真实验证

只有在用户明确授权后，才做一次真实 Bark 验证：

1. 完成一个很小的 Codex 回合。
2. 确认 Stop Hook 状态消息出现。
3. 检查 iPhone 是否收到标题为本机机器标签、正文为当前 Session 标题的通知；若 Session 尚未命名，则正文为“本轮回复已结束”。
4. 只记录脱敏后的 HTTP 状态和耗时，不记录 Key、请求 URL 或对话内容。

HTTP 200 只表示 Bark 接受了请求，不代表 APNs 一定已经在手机上显示；还要检查锁屏通知、横幅、声音和 Focus 设置。

## 常见问题

| 现象 | 检查方向 |
| --- | --- |
| 仍看到旧 `/Users/.../.codex/skills/bark-notifications/...` 报错 | 结束迁移前启动的 Codex Desktop/app-server 或 CLI 会话并重新启动；不要恢复旧 `hooks.json` |
| 看不到 Hook 状态消息 | `hooks.json` 层级、Hook 功能开关、JSON 语法、Codex 重启和 `/hooks` 信任状态 |
| 有状态消息但没有 Bark | `bark-task-complete` 的 dry-run、钥匙串 service/account、网络和 Bark API 状态 |
| `credential-unavailable` | 本机没有正确保存 `codex-bark-notifications` / `codex` 项目 |
| 同一用户回合收到多次 | 先确认本机安装版包含 `CODEX_THREAD_ID` 主线程过滤，再检查是否同时配置了用户级和项目级相同 Stop Hook |
| 标题或正文显示回退文案 | 机器标签配置或 Thread 标题暂时不可用；检查本机标签配置、`CODEX_THREAD_ID` 和 `thread/read` 元数据读取 |
| 通知没有声音或不显示 | `level`、Bark sound、iOS 通知权限、Focus 模式和 Bark 历史记录 |

通知失败不会阻止 Codex 本轮回复，也不会自动重试。通知不读取或发送对话正文。需要修改发送参数时，只修改插件源码中的发送入口，再重新安装或刷新插件。
