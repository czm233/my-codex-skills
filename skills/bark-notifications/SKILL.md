---
name: bark-notifications
description: Use when sending, integrating, testing, or troubleshooting Bark iOS push notifications through api.day.app or a self-hosted Bark server, including GET/POST/JSON requests, sound/level/group/url parameters, APNs delivery diagnosis, and secret-safe configuration.
---

# Bark Notifications

Use Bark as an iOS system-notification channel. Prefer the official tutorial and API reference in [references/bark-api.md](references/bark-api.md) when exact parameters or server-version behavior matters.

## Safety and credential boundary

- Treat a Bark Device Key like a password. Never ask the user to paste it into chat, repeat it, put it in a URL shown in a response, or commit it.
- Do not read, print, grep, validate, or summarize `.env` contents. A running backend may load configuration at runtime; the agent must not inspect the values.
- Redact keys from logs and errors. Do not log the full request URL because the public Bark URL normally contains the key.
- Send only non-sensitive status information by default. Do not send conversation text, API keys, cookies, or source paths.

## Codex turn notification hook integration

The automatic Codex turn notification is part of this Skill package:

- `bin/bark-stop-hook` runs for Stop events, ignores internal or ephemeral turns when their `session_id` differs from the visible `CODEX_THREAD_ID`, deduplicates accepted events by `session_id + turn_id`, reads only the current thread metadata (`thread/read` with `includeTurns: false`) to use its user-facing name as the Bark title, and falls back to `Codex` when that metadata is unavailable. When `CODEX_THREAD_ID` is unavailable, it preserves the per-session behavior for compatibility. It does not ask Codex to start another model turn or read transcript items.
- `bin/bark-task-complete` is the single status sender. It reads the Bark Device Key from the macOS Keychain, resolves the local machine label, and sends a title in the form `[机器标签] 任务标题` with the fixed, non-sensitive message “本轮回复已结束”.
- `bin/bark-configure-machine` writes the non-secret per-computer label to `${CODEX_HOME}/bark-notifications.json`. Keep this file outside the Skill directory and repository so every computer can use the same Skill source with a different local label.

The user-level Stop Hook must invoke these installed Skill files. Do not create a second Bark sender under `~/.codex/bin`, embed a `curl` request in `hooks.json`, or make the Stop Hook continue the model so it can re-read this Markdown file. The Markdown Skill remains the source of Bark API and safety guidance, while the two bundled commands provide the deterministic lifecycle integration.

For setting up this integration on another computer, read [references/codex-hook-setup.md](references/codex-hook-setup.md). It covers the machine-label configuration contract, local Keychain storage, merging the user-level Hook configuration, Hook trust review, dry-run verification, and troubleshooting without putting a Device Key in the repository or chat.

## Choose the smallest interface

1. For a one-off user smoke test, use the Bark App's locally copied test URL or a `curl` request with a placeholder key. The user runs it locally; do not request the key.
2. For backend integration, prefer `POST` with JSON to the public endpoint `https://api.day.app/<DEVICE_KEY>` so title/body and parameters do not need path encoding.
3. For a self-hosted Bark server using API v2, POST JSON to `/push` and put `device_key` in the JSON body.
4. Use GET path syntax only for short, URL-safe manual tests. URL-encode non-ASCII text, spaces, newlines, `?`, `&`, `#`, `%`, and slashes in path segments.

## Minimal manual smoke test

Use a new key locally; never replace the placeholder in a chat message:

```bash
curl --fail --silent --show-error \
  -X POST 'https://api.day.app/<DEVICE_KEY>' \
  -H 'Content-Type: application/json; charset=utf-8' \
  -d '{"title":"Codex test","body":"Bark is connected","level":"active","sound":"bell","group":"codex"}'
```

The expected HTTP result is a successful JSON response. A successful API response means that Bark accepted the push request; it does not prove that APNs has already displayed the alert. Test with the iPhone locked and check the system notification, not only Bark's history screen.

For a GET smoke test, the official path forms are:

```text
/<DEVICE_KEY>/<BODY>
/<DEVICE_KEY>/<TITLE>/<BODY>
/<DEVICE_KEY>/<TITLE>/<SUBTITLE>/<BODY>
```

Query parameters follow the path, for example `?level=active&sound=bell`. Do not confuse a path segment such as `/sound=bell` with a query parameter: it is just the body text `sound=bell`.

## Backend integration rules

- Load `BARK_ENABLED`, `BARK_BASE_URL`, and `BARK_DEVICE_KEY` only inside the running backend process. Keep the example configuration empty.
- Build the endpoint from a validated base URL and key in memory; never expose the resulting URL.
- Send a small JSON payload such as `title`, `body`, `level`, `sound`, and `group`. Keep bodies concise and non-sensitive.
- Set a short connect/read timeout. Notification failure must not mark the primary job as failed or roll back already-committed work.
- Log only an event name, HTTP status, request id if provided, duration, and a redacted error category. Never log title/body if they can contain private content.
- Use a stable group such as `codex-learning` and an explicit `level` (`active` for normal immediate alerts). Use `timeSensitive` only when the user expects Focus-mode delivery. Use `critical` only after the user has granted iOS/Bark critical-alert permission; it is not a way to bypass all policy.
- Keep an opt-out switch and a dry-run/test path that never sends a real notification unless the user explicitly requests the external side effect.

## Diagnose failures

- `200` / success: Bark accepted the request. Check APNs/iOS delivery separately.
- `400` with “failed to get device token”: the key is unknown, revoked, or the device is no longer registered. Re-register the device; do not retry the same exposed key.
- `curl -i` prints response headers. `HTTP/1.1 200 Connection established` is commonly a proxy CONNECT line, not a Bark error.
- A server timestamp is not request duration. Measure latency with `curl -sS -o /dev/null -w 'status=%{http_code} total=%{time_total}s\\n' ...`.
- If an exact `curl` request works but clicking a web link does not, treat the browser/link client as the problem. Browsers may preview or block side-effect GET requests; backend code should issue the HTTP request directly.
- If the push arrives without sound, verify `level=active`, a sound file supported by the installed Bark version (for example `bell`), iOS notification sound settings, Focus mode, and the Bark app's sound selection. `passive` intentionally does not light the screen.
- If Chinese or punctuation causes failure, URL-encode GET path/query values or switch to JSON POST.

## Verification before declaring success

1. Confirm the user has installed Bark and registered the device without sharing the key.
2. Run one local smoke test using a fresh key and a harmless message.
3. Record the HTTP status and elapsed time without recording the key or message body.
4. Verify the iPhone lock-screen/banner/sound behavior; an entry in Bark history alone is insufficient.
5. For an integration change, mock the HTTP client in automated tests and perform one explicit real-device test only after the user authorizes it.
