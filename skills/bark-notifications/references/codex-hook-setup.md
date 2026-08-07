# Codex Stop Hook 配置指南

本文记录如何在任意 macOS 电脑上安装 `bark-notifications`，并把它接入 Codex 的用户级 `Stop` Hook。配置目标是：每次 Codex 用户可见主线程结束一个回合时，发送一次 Bark 通知“本轮回复已结束”，标题格式为 `[本机机器标签] 当前 Thread 名称`；如果 Thread 名称查询失败，则任务标题回退为 `Codex`。同一个 `session_id + turn_id` 只发送一次，Codex Desktop 为界面功能启动的内部临时 turn 不发送。

## 先理解组成部分

Skill 目录中已经包含三条可执行命令：

- `bin/bark-stop-hook`：接收 Codex 的 `Stop` 事件；存在 `CODEX_THREAD_ID` 时先确认事件 `session_id` 与当前可见线程一致，不一致的内部临时 turn 直接跳过；随后去重，调用 Codex App Server 的 `thread/read`（`includeTurns: false`，只取元数据），再调用发送器。未提供 `CODEX_THREAD_ID` 的 Codex 表面保持原有按事件会话通知的兼容行为。
- `bin/bark-task-complete`：解析本机机器标签，从 macOS 钥匙串读取 Bark Device Key，通过 Bark `/push` 接口发送带机器前缀的标题和固定正文。
- `bin/bark-configure-machine`：写入或显示本机非敏感机器标签，不读取或处理 Bark Key。

用户级 `hooks.json` 只负责把 Codex 的 `Stop` 生命周期事件指向第一条命令。不要在 `hooks.json` 中嵌入 `curl`，也不要在 `~/.codex/bin` 再复制一份 Bark 发送脚本。

## 安装 Skill

在目标电脑的 Codex 中使用 Skill Installer，从仓库安装本 Skill：

```text
使用 $skill-installer 从 czm233/my-codex-skills 安装：
skills/bark-notifications
```

安装完成后，确认以下文件存在。`CODEX_HOME` 未设置时，默认值是 `~/.codex`：

```text
${CODEX_HOME:-$HOME/.codex}/skills/bark-notifications/SKILL.md
${CODEX_HOME:-$HOME/.codex}/skills/bark-notifications/bin/bark-stop-hook
${CODEX_HOME:-$HOME/.codex}/skills/bark-notifications/bin/bark-task-complete
${CODEX_HOME:-$HOME/.codex}/skills/bark-notifications/bin/bark-configure-machine
```

如果本机已经有同名 Skill，先比较版本，再按 Skill Installer 的重新安装流程更新；不要静默覆盖本机独立修改。

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
SKILL_HOME="${CODEX_HOME:-$HOME/.codex}/skills/bark-notifications"
"$SKILL_HOME/bin/bark-configure-machine" --machine-label "<用户确认的短标签>"
"$SKILL_HOME/bin/bark-configure-machine" --show
```

如果已有配置，命令会拒绝静默覆盖不同标签；用户明确要求更换时才追加 `--force`。配置文件权限由命令设置为仅当前用户可读写。

通知标题示例（仅为格式示例，不是固定设备名）：

```text
[<本机机器标签>] <当前 Codex 任务标题>
本轮回复已结束
```

通知分组也会包含机器标签，以便在 Bark 历史记录中按电脑区分。标题前缀是主要识别方式，适合 Apple Watch 的紧凑通知展示。

## 合并用户级 hooks.json

先检查目标电脑是否已经有 `hooks.json` 或 `config.toml` 中的其他 Hook。只合并下面的 `Stop` 项，不要覆盖已有的 `PreToolUse`、`PostToolUse`、Computer Use `notify` 或其他配置。

Hook 命令必须使用目标电脑实际的 `CODEX_HOME` 路径。下面的 `/ABSOLUTE/CODEX_HOME` 是占位符，不能原样复制：

```json
{
  "description": "Send Bark after every completed Codex turn.",
  "hooks": {
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/usr/bin/python3 /ABSOLUTE/CODEX_HOME/skills/bark-notifications/bin/bark-stop-hook",
            "timeout": 30,
            "statusMessage": "Sending Bark turn notification"
          }
        ]
      }
    ]
  }
}
```

例如，默认 `CODEX_HOME` 为 `~/.codex` 的电脑，命令实际应展开为类似下面的绝对路径：

```text
/Users/<用户名>/.codex/skills/bark-notifications/bin/bark-stop-hook
```

不要在 JSON 中依赖未展开的 `~`、`$HOME` 或 `$CODEX_HOME`；Hook 命令需要稳定的绝对路径。若 Codex 使用项目级 `.codex/hooks.json`，仍应确认该项目层已被信任，并避免与用户级 Hook 重复发送。

确认 Codex 的 Hook 功能已启用。不同 Codex 版本的配置键可能不同，应先读取本机现有配置，再按当前版本的配置文档启用；不要覆盖无关配置。

## 审核并信任 Hook

非托管命令 Hook 需要人工审核。启动或重新加载 Codex 后：

1. 在 Codex CLI 执行 `/hooks`。
2. 找到新增或变更的 Bark `Stop` Hook。
3. 审核命令路径与脚本内容，确认它只读取钥匙串并向 Bark 发送固定消息。
4. 信任该 Hook。

Hook 定义或脚本发生变化后，可能需要重新审核；不要使用绕过信任的危险选项作为长期配置。

## Dry-run 验证

先只验证发送器，不访问钥匙串或 Bark：

```bash
SKILL_HOME="${CODEX_HOME:-$HOME/.codex}/skills/bark-notifications"
printf '%s' 'Bark Hook dry-run' | \
  "$SKILL_HOME/bin/bark-task-complete" turn_stopped --dry-run
```

预期输出类似：

```text
status=dry-run event=turn_stopped sent=false
```

再验证 Stop Hook 的去重路径。下面的测试使用临时状态目录，不发送真实通知：

```bash
SKILL_HOME="${CODEX_HOME:-$HOME/.codex}/skills/bark-notifications"
TEST_STATE_DIR="$(mktemp -d)"
printf '%s' '{"hook_event_name":"Stop","session_id":"dry-run-session","turn_id":"dry-run-turn","stop_hook_active":false}' | \
  CODEX_THREAD_ID="dry-run-session" \
  CODEX_BARK_HOOK_DRY_RUN=1 \
  CODEX_BARK_HOOK_STATE_DIR="$TEST_STATE_DIR" \
  /usr/bin/python3 "$SKILL_HOME/bin/bark-stop-hook"
```

预期 Hook 输出为 `{}`，并且临时目录中只出现一个去重文件。相同 `session_id + turn_id` 再运行一次，不应新增文件。

再用一个不同的事件会话验证内部 turn 过滤：

```bash
printf '%s' '{"hook_event_name":"Stop","session_id":"internal-session","turn_id":"internal-turn","stop_hook_active":false}' | \
  CODEX_THREAD_ID="dry-run-session" \
  CODEX_BARK_HOOK_DRY_RUN=1 \
  CODEX_BARK_HOOK_STATE_DIR="$TEST_STATE_DIR" \
  /usr/bin/python3 "$SKILL_HOME/bin/bark-stop-hook"
```

预期仍输出 `{}`，临时目录中的去重文件数量不变，表示内部临时 turn 没有进入通知链路。测试兼容回退时，可通过 `env -u CODEX_THREAD_ID` 执行原有 Dry-run；此时有效 Stop 事件仍按 `session_id + turn_id` 去重和通知。

## 真实验证

只有在用户明确授权后，才做一次真实 Bark 验证：

1. 完成一个很小的 Codex 回合。
2. 确认 Stop Hook 状态消息出现。
3. 检查 iPhone 是否收到“本轮回复已结束”。
4. 只记录脱敏后的 HTTP 状态和耗时，不记录 Key、请求 URL 或对话内容。

HTTP 200 只表示 Bark 接受了请求，不代表 APNs 一定已经在手机上显示；还要检查锁屏通知、横幅、声音和 Focus 设置。

## 常见问题

| 现象 | 检查方向 |
| --- | --- |
| 看不到 Hook 状态消息 | `hooks.json` 层级、Hook 功能开关、JSON 语法、Codex 重启和 `/hooks` 信任状态 |
| 有状态消息但没有 Bark | `bark-task-complete` 的 dry-run、钥匙串 service/account、网络和 Bark API 状态 |
| `credential-unavailable` | 本机没有正确保存 `codex-bark-notifications` / `codex` 项目 |
| 同一用户回合收到多次 | 先确认本机安装版包含 `CODEX_THREAD_ID` 主线程过滤，再检查是否同时配置了用户级和项目级相同 Stop Hook |
| 标题显示 `Codex` | 当前 Thread 没有设置名称，或 Hook 无法启动 App Server / 查询 `thread/read`；通知正文仍会正常发送 |
| 通知没有声音或不显示 | `level`、Bark sound、iOS 通知权限、Focus 模式和 Bark 历史记录 |

通知失败不会阻止 Codex 本轮回复，也不会自动重试。会话名称查询失败时仍会发送通知，只把标题回退为 `Codex`；查询不会读取或发送对话正文。需要修改发送参数时，只修改 Skill 源码中的发送入口，再重新同步本机安装版本。
