#!/usr/bin/env python3
"""Token Plan 额度查询 / 控制台授权（纯标准库，不依赖 bl CLI）。

  quota.py                 查询额度
  quota.py login           打开授权页，回写 token 后自动查一次
  quota.py logout          删除本地 token
  --json                   机器可读输出
  --no-browser             只打印授权链接，不自动开浏览器

token 存放：~/.config/token-plan-quota/token（0600）。永不打印 token。
"""
import argparse
import json
import os
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread

CONSOLE_ORIGIN = "https://bailian.console.aliyun.com"
GATEWAY_URL = "https://bailian-cs.console.aliyun.com/cli/api.json"
GATEWAY_ACTION = "BroadScopeAspnGateway"
GATEWAY_PRODUCT = "sfm_bailian"
REGION = "cn-beijing"
USAGE_API = "zeldaHttp.apikeyMgr./tokenplan/personal/api/v2/usage"
SUBSCRIPTION_API = "zeldaHttp.apikeyMgr./tokenplan/personal/api/v2/subscription"
CREDITS_BY_PLAN = {"lite": 20000, "essential": 45000, "standard": 80000, "pro": 200000}
TOKEN_PATH = os.path.expanduser("~/.config/token-plan-quota/token")
TZ = timezone(timedelta(hours=8))


def read_token():
    try:
        with open(TOKEN_PATH) as f:
            return f.read().strip() or None
    except FileNotFoundError:
        return None


def write_token(token):
    d = os.path.dirname(TOKEN_PATH)
    os.makedirs(d, mode=0o700, exist_ok=True)
    fd = os.open(TOKEN_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(token)
    os.chmod(TOKEN_PATH, 0o600)


def call_console(api, token, data=None):
    params = json.dumps({
        "Api": api,
        "V": "1.0",
        "Data": {
            **(data or {}),
            "cornerstoneParam": {
                "protocol": "V2",
                "console": "ONE_CONSOLE",
                "productCode": "p_efm",
                "switchUserType": 3,
                "consoleSite": "BAILIAN_ALIYUN",
            },
        },
    }, separators=(",", ":"))
    url = (f"{GATEWAY_URL}?action={GATEWAY_ACTION}&product={GATEWAY_PRODUCT}"
           f"&api={urllib.parse.quote(api, safe='')}")
    body = urllib.parse.urlencode({"params": params, "region": REGION}).encode()
    req = urllib.request.Request(url, data=body, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "*/*",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)
    inner = payload.get("data") or {}
    if inner.get("success") is False:
        code = inner.get("errorCode") or ""
        raise PermissionError(code or "gateway_error")
    return ((inner.get("DataV2") or {}).get("data") or {}).get("data") or {}


def fmt_reset(ms):
    return datetime.fromtimestamp(ms / 1000, TZ).strftime("%Y-%m-%d %H:%M")


def cmd_query(as_json=False):
    token = read_token()
    if not token:
        print("没有本地 token，先运行：quota.py login", file=sys.stderr)
        return 2
    try:
        usage = call_console(USAGE_API, token)
    except PermissionError as e:
        if "NotLogined" in str(e):
            print("token 已失效（Login.NotLogined），运行：quota.py login", file=sys.stderr)
            return 3
        print(f"接口返回错误：{e}", file=sys.stderr)
        return 1

    pct = usage.get("per1MonthPercentage")
    reset = usage.get("per1MonthResetTime")
    plan = end = None
    try:
        sub = call_console(SUBSCRIPTION_API, token)
        plan = sub.get("specCode")
        if sub.get("endTime"):
            end = datetime.fromtimestamp(sub["endTime"] / 1000, TZ).strftime("%Y-%m-%d")
    except Exception:
        pass

    total = CREDITS_BY_PLAN.get((plan or "").lower())
    out = {
        "plan": plan,
        "percentageUsed": pct,
        "resetTime": fmt_reset(reset) if reset else None,
        "subscriptionEnds": end,
        "creditsTotal": total,
        "creditsUsed": round(pct * total) if (pct is not None and total) else None,
    }
    if as_json:
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    if pct is None:
        print("没有额度数据（该接口未返回 per1MonthPercentage）")
        return 0
    line = f"已用 {pct * 100:.2f}%"
    if total:
        line += f"（≈{round(pct * total):,} / {total:,} Credits，剩 {round((1 - pct) * total):,}）"
    print(line)
    if reset:
        print(f"重置 {fmt_reset(reset)}")
    if plan:
        print(f"套餐 {plan}" + (f"，到期 {end}" if end else ""))
    return 0


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


class Callback(BaseHTTPRequestHandler):
    token = None
    state = None
    done = False

    def log_message(self, *args):
        pass

    def _cors(self):
        origin = self.headers.get("Origin")
        if origin == CONSOLE_ORIGIN:
            self.send_header("Access-Control-Allow-Origin", CONSOLE_ORIGIN)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Vary", "Origin, Access-Control-Request-Private-Network")

    def _reply(self, code, body):
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode())

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        if self.headers.get("Access-Control-Request-Private-Network") == "true":
            self.send_header("Access-Control-Allow-Private-Network", "true")
        self.end_headers()

    def do_GET(self):
        self._handle(None)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        self._handle(self.rfile.read(min(n, 65536)) if n else b"")

    def _handle(self, raw):
        u = urllib.parse.urlparse(self.path)
        q = urllib.parse.parse_qs(u.query)
        if (q.get("state") or [None])[0] != self.state:
            return self._reply(400, "bad state")
        token = (q.get("access_token") or q.get("accessToken") or [None])[0]
        if not token and raw:
            body = raw.decode("utf-8", "replace")
            try:
                token = json.loads(body).get("access_token")
            except Exception:
                token = (urllib.parse.parse_qs(body).get("access_token") or [None])[0]
        if not token:
            return self._reply(400, "missing access_token")
        self.__class__.token = token.strip()
        self.__class__.done = True
        self._reply(200, "OK")
        Thread(target=self.server.shutdown, daemon=True).start()

    def log_message_default(self, *a):
        pass


def cmd_login(no_browser=False, timeout=900):
    port = free_port()
    state = secrets.token_hex(16)
    Callback.state = state
    Callback.token = None
    Callback.done = False
    srv = HTTPServer(("127.0.0.1", port), Callback)
    url = f"{CONSOLE_ORIGIN}/console-login?notice=127.0.0.1:{port}?state={state}"
    print(f"授权链接：{url}")
    if not no_browser:
        try:
            subprocess.run(["open", url], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("已尝试在默认浏览器打开，请在页面里完成授权。")
        except Exception:
            print("无法自动打开浏览器，请手动粘贴上面的链接。")
    wait_txt = f"{timeout // 60} 分钟" if timeout >= 60 else f"{timeout} 秒"
    print(f"等待回调（最多 {wait_txt}）…", flush=True)
    srv.timeout = 1
    deadline = time.time() + timeout
    while time.time() < deadline and not Callback.done:
        srv.handle_request()
    srv.server_close()
    if not Callback.done:
        print("超时，没有收到 token。", file=sys.stderr)
        return 4
    write_token(Callback.token)
    print(f"token 已保存到 {TOKEN_PATH}")
    return cmd_query()


def cmd_logout():
    try:
        os.remove(TOKEN_PATH)
        print("已删除本地 token。")
    except FileNotFoundError:
        print("本地没有 token。")
    return 0


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("command", nargs="?", default="query", choices=["query", "login", "logout"])
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()
    if a.command == "login":
        return cmd_login(a.no_browser, a.timeout)
    if a.command == "logout":
        return cmd_logout()
    return cmd_query(a.json)


if __name__ == "__main__":
    sys.exit(main())