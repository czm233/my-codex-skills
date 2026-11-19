---
name: token-plan-quota
description: 查询阿里云百炼 Token Plan（订阅套餐）额度用量与重置时间，或控制台登录态过期时重新授权。用户问“百炼额度/Token Plan 还剩多少/积分用掉多少/是不是过期了”时使用。纯 Python 标准库，不依赖百炼 bl CLI。
---

# Token Plan 额度查询

一个脚本，两个动作：查额度、重新授权。不要为这件事安装或恢复 `bl`。

```bash
python3 ~/.dsh/skills/token-plan-quota/scripts/quota.py           # 查额度
python3 ~/.dsh/skills/token-plan-quota/scripts/quota.py login     # 授权（会弹浏览器）
python3 ~/.dsh/skills/token-plan-quota/scripts/quota.py --json    # 机器可读
```

输出示例：

```
已用 51.61%（≈103,215 / 200,000 Credits，剩 96,785）
重置 2026-11-30 00:00
套餐 pro，到期 2026-12-01
```

## 判定与流程

1. 用户问额度 → 直接跑查询，不要先问他套餐、不要先登录。
2. 退出码 `3` 或提示 `Login.NotLogined` → token 过期，跑 `login`：浏览器会弹出百炼授权页，用户点授权后脚本自动保存 token 并顺手查一次。
3. 退出码 `2` → 本地没 token，同样跑 `login`。
4. 只读查询，不产生模型调用费用；不需要征求计费确认。

## 实现要点（改脚本时看）

- 额度接口：`POST https://bailian-cs.console.aliyun.com/cli/api.json?action=BroadScopeAspnGateway&product=sfm_bailian&api=<URL编码的接口名>`
  Header `Authorization: Bearer <控制台 access_token>`，body 为 form-urlencoded：`params=<JSON>&region=cn-beijing`。
  `params` 形如 `{"Api":"<接口名>","V":"1.0","Data":{"cornerstoneParam":{"protocol":"V2","console":"ONE_CONSOLE","productCode":"p_efm","switchUserType":3,"consoleSite":"BAILIAN_ALIYUN"}}}`。
- 额度接口名 `zeldaHttp.apikeyMgr./tokenplan/personal/api/v2/usage`，返回 `per1MonthPercentage` / `per1MonthResetTime`。
- 订阅接口名 `zeldaHttp.apikeyMgr./tokenplan/personal/api/v2/subscription`，返回 `specCode`（套餐档）、`endTime`。同一套请求格式，换接口名即可。
- 授权：本地起 `127.0.0.1` 随机端口，`state` 为 16 字节随机十六进制，打开
  `https://bailian.console.aliyun.com/console-login?notice=127.0.0.1:<port>?state=<state>`，
  页面授权后回调 `http://127.0.0.1:<port>/?state=<state>&access_token=<token>`（也兼容 POST JSON），校验 state 后保存。
- token 存 `~/.config/token-plan-quota/token`（0600）。**任何输出、日志、回复都不要打印 token 内容**，只报告“已保存/已失效”。
- 额度百分比约 6 位小数，可用于差值测量；但同一账号可能有其他客户端在调用，采样窗口要短。

## 常见错误

| 现象 | 处理 |
| --- | --- |
| `Login.NotLogined` | token 失效，跑 `login` |
| 回调超时（默认 15 分钟） | 用户没点授权，或浏览器拦了 127.0.0.1 回调；重跑 `login` |
| `bad state` | 授权链接被重复打开或状态不匹配，重跑 `login` |
| 没有 `per1MonthPercentage` | 该账号没有 Token Plan 订阅（或查错了站点） |