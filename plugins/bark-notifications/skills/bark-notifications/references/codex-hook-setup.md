# Codex Stop Hook 配置指南

本文记录如何在任意 macOS 电脑上安装用户级 `bark-notifications` 插件。插件启用并信任后，每次 Codex 用户可见主线程结束一个回合时发送一次 Bark 通知：标题为“当前 Session 的用户可见标题 · 原机器名称”，正文为最后一条回复的前 30 个字符，截断时追加省略号。同一个 `session_id + turn_id` 只发送一次，Codex Desktop 为界面功能启动的内部临时 turn 不发送。插件停用或卸载后，插件 Hook 不再加载。

## 先理解组成部分

插件中包含三条可执行命令和一个生命周期 Hook：

- `hooks/hooks.json`：插件自带的用户级 `Stop` Hook，不修改 `~/.codex/hooks.json`。
- `bin/bark-stop-hook`：接收插件的 `Stop` 事件；存在 `CODEX_THREAD_ID` 时先确认事件 `session_id` 与当前可见线程一致，不一致的内部临时 turn 直接跳过；随后去重，再调用发送器。未提供 `CODEX_THREAD_ID` 的 Codex 表面保持原有按事件会话通知的兼容行为。
- `bin/bark-task-complete`：解析本机机器标签，从 macOS 钥匙串读取 Bark Device Key，通过 Bark `/push` 接口发送经过清洗的 Session 标题与回复预览，机器标签用于分组。
- `bin/bark-configure-machine`：写入或显示本机非敏感机器标签，不读取或处理 Bark Key。

插件 Hook 通过运行时的插件根模板变量调用 Skill 内脚本：ZCode 使用 `${CLAUDE_PLUGIN_ROOT}`（或 `${ZCODE_PLUGIN_ROOT}`），Codex 使用 `${PLUGIN_ROOT}`。仓库自带的 `hooks/hooks.json` 写的是 ZCode 变量；在 Codex 上安装时需把它替换为 `${PLUGIN_ROOT}`。不要手动编辑 `~/.codex/hooks.json`，也不要在 `~/.codex/bin` 再复制一份 Bark 发送脚本。

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

完成迁移后必须重启 Codex Desktop，或结束并重新启动对应的 Codex CLI/app-server 会话。Codex 会在会话启动时加载 Hook；已经运行的旧会话可能仍在内存中保留旧 `hooks.json`，即使磁盘上的旧文件已经删除，也会继续尝试执行旧路径并报“文件不存在”。重启后用 `/hooks` 确认 Stop Hook 的来源显示为 `bark-notifications@my-codex-skills`，命令路径包含当前运行时的插件根变量（Codex 为 `${PLUGIN_ROOT}`，ZCode 为 `${CLAUDE_PLUGIN_ROOT}`）；不要为了消除旧报错重新创建旧用户级 Hook。

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

通知标题使用“Session 标题 · 原机器名称”，正文使用回复前 30 个字符。机器标签同时用于 Bark 分组：

```text
MacBook Air
skill维护-bark-notifications
```

通知分组会包含机器标签，以便在 Bark 历史记录中按电脑区分。Session 标题只读取 `thread.name` 元数据，回复预览只取 Stop 事件的 `last_assistant_message`，不读取转录文件或请求历史回合；如果 Thread 尚未命名、读取失败或标题仅为“本轮回复已结束 / 本轮会话已结束”，自动 Hook 静默跳过，不发送无有效标题的通知。独立发送器的手动调用仍保留安全回退文案。

## 自定义通知铃声

发送器从上述本机 JSON 配置读取可选的 `sound` 字段。未配置、配置无法读取或值无效时使用 `bell`。名称最长 120 字符，不能包含路径分隔符或控制字符；使用铃声名称，不带 `.caf` 扩展名。

如需降低普通通知的响度，可先将音频降低音量，导出为不超过 30 秒的 `.caf` 文件，在接收通知的 iPhone 上导入 Bark。确认导入完成后，保留 JSON 中其他字段，仅新增或更新 `"sound": "bell_quiet"`（示例名称，必须与手机中导入的名称一致）。不要把个人铃声选择硬编码进插件或同步给其他电脑。

普通 `active` 通知不支持用 `volume` 参数单独调节音量。保持现有级别即可，不要为调音量切换为会绕过静音设置的 `critical`。

本机配置修改后，下一次发送时读取，无需重新加载 Hook。先用模拟请求确认 `sound` 参数，再让正常 Stop Hook 触发一次通知并由用户确认声音。发送器无法检查手机是否已有该铃声；名称不存在时可能响起系统默认音效。

## 插件 Hook 生命周期

不需要合并或编辑用户级 `hooks.json`。Codex 从已启用插件中加载 `hooks/hooks.json`，命令使用插件根模板变量定位插件内脚本（Codex 为 `${PLUGIN_ROOT}`，ZCode 为 `${CLAUDE_PLUGIN_ROOT}`，仓库自带文件使用后者）。插件 Hook 与用户级、项目级 Hook 共同加载；如果另一层仍配置旧 Bark Hook，会造成重复通知，因此迁移时要删除旧 Bark Hook。

ZCode 与 Codex 的差异：ZCode 通过插件清单自动发现 `hooks/hooks.json`，无需 `/hooks` 信任审核，可在 Settings → Plugin Management 的插件详情中查看 Hook 是否可运行；Hook 的触发、超时与失败记录在 ZCode 日志中。ZCode 支持的事件名恰为 `SessionStart`、`UserPromptSubmit`、`PreToolUse`、`PermissionRequest`、`PostToolUse`、`PostToolUseFailure`、`Stop` 七种，本插件的 `Stop` Hook 无需改动即可被 ZCode 加载。

插件停用或卸载后，Codex 不再加载该插件的 Hook；这不会删除用户主动配置的其他 Hook，也不会删除 Keychain 中的 Bark Key 或机器标签配置。

## 审核并信任 Hook

非托管命令 Hook 需要人工审核。启动或重新加载 Codex 后：

1. 在 Codex CLI 执行 `/hooks`。
2. 找到新增或变更的 Bark `Stop` Hook。
3. 审核命令路径与脚本内容，确认它只读取钥匙串、Thread 标题元数据和 Stop 事件自带的最后回复，向 Bark 发送会话标题与原机器名称组成的标题，以及回复前 30 个字符；机器标签也用于分组。
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
3. 检查 iPhone 是否收到标题为“当前 Session 标题 · 原机器名称”、正文为回复前 30 个字符的通知；若 Session 尚未命名或标题读取失败，则应无通知。
4. 只记录脱敏后的 HTTP 状态和耗时，不记录 Key、请求 URL 或对话内容。

HTTP 200 只表示 Bark 接受了请求，不代表 APNs 一定已经在手机上显示；还要检查锁屏通知、横幅、声音和 Focus 设置。

## 常见问题

| 现象 | 检查方向 |
| --- | --- |
| 仍看到旧 `/Users/.../.codex/skills/bark-notifications/...` 报错 | 结束迁移前启动的 Codex Desktop/app-server 或 CLI 会话并重新启动；不要恢复旧 `hooks.json` |
| 报错路径形如 `/skills/bark-notifications/bin/bark-stop-hook`（缺少前缀） | Hook 命令里的插件根变量没有被运行时展开（展开为空）。ZCode 需使用 `${CLAUDE_PLUGIN_ROOT}`，Codex 需使用 `${PLUGIN_ROOT}`；核对 `hooks/hooks.json` 与当前运行时是否匹配 |
| 看不到 Hook 状态消息 | `hooks.json` 层级、Hook 功能开关、JSON 语法、Codex 重启和 `/hooks` 信任状态 |
| 有状态消息但没有 Bark | `bark-task-complete` 的 dry-run、钥匙串 service/account、网络和 Bark API 状态 |
| `credential-unavailable` | 本机没有正确保存 `codex-bark-notifications` / `codex` 项目 |
| 同一用户回合收到多次 | 先确认本机安装版包含 `CODEX_THREAD_ID` 主线程过滤，再检查是否同时配置了用户级和项目级相同 Stop Hook |
| 标题或正文显示回退文案 | 机器标签配置或 Thread 标题暂时不可用；检查本机标签配置、`CODEX_THREAD_ID` 和 `thread/read` 元数据读取 |
| 通知没有声音或不显示 | `level`、Bark sound、iOS 通知权限、Focus 模式和 Bark 历史记录 |

通知失败不会阻止 Codex 本轮回复，也不会自动重试。通知仅发送用户要求的最后回复前 30 个字符，不读取转录文件，不发送完整回复或历史对话。需要修改发送参数时，只修改插件源码中的发送入口，再重新安装或刷新插件。


## 本机诊断记录

Stop Hook 自动将分类结果写入 `${PLUGIN_DATA}/bark-stop-hook/diagnostics.jsonl`；未设置 `PLUGIN_DATA` 时位于 `${CODEX_HOME:-~/.codex}/state/bark-stop-hook/diagnostics.jsonl`。自定义 `CODEX_BARK_HOOK_STATE_DIR` 时使用该目录。无需启用额外开关，也不额外发送诊断通知。

记录仅包含 UTC 时间、结果、固定原因分类、会话与回合 ID 的哈希、当前线程与事件会话的匹配关系及 dry-run 标志；不保存标题、正文、原始 ID、路径、错误原文或凭证。日志权限为 `0600`，超过约 1 MiB 时轮换，仅保留当前和上一份；写入失败不影响主任务。

- `session_mismatch` + `mismatch`：事件会话与当前线程不同，已过滤，符合内部临时会话特征；该字段不能单独证明内部任务的具体用途。
- `unavailable`：没有 `CODEX_THREAD_ID`，无法据此判断是否内部会话。
- `process_start_failed` / `process_exited`：标题查询进程无法启动或提前退出。
- `initialize_no_response` / `thread_read_no_response`：等待期内未得到有效响应，可能超时或协议无效，不能直接断言是超时。
- `initialize_error` / `thread_read_error`：接口明确返回错误。
- `empty_or_invalid_title` / `generic_title`：无有效标题，已静默跳过。
- `sender_ok`：发送器正常退出；dry-run 不会发送，真实调用也不代表手机已经显示通知。
- `missing_reply_preview`：Stop 事件未提供有效 `last_assistant_message`，跳过通知；不回读历史对话。
- `duplicate`：同一事件再次触发，已去重。

再次出现异常时，按手机时间换算 UTC 后检查对应记录，用哈希关联同一会话的事件。若仍缺少可关联记录，不能断言通知来源。

电脑名称后缀沿用修改前的机器标签解析规则（环境变量 → 本机配置 → macOS 电脑名称 → 安全回退），保留既有安全清洗与长度限制，不另取简短名称。会话标题的截断在拼接后缀之前完成。手机实际显示行数由 iOS 决定。
