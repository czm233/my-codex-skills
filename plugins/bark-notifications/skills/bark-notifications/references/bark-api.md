# Bark API reference

Use the official tutorial as the source of truth:

- <https://bark.day.app/#/tutorial>
- <https://github.com/Finb/Bark>
- <https://github.com/Finb/bark-server>

## Request forms

The public service accepts GET and POST requests. The legacy URL forms are:

```text
/:key/:body
/:key/:title/:body
/:key/:title/:subtitle/:body
```

Example with placeholders only:

```bash
curl --fail --silent --show-error \
  'https://api.day.app/<DEVICE_KEY>/Codex/Finished?level=active&sound=bell'
```

For user text containing non-ASCII characters or reserved URL characters, encode each value or use JSON POST.

### Form POST

```bash
curl --fail --silent --show-error \
  -X POST 'https://api.day.app/<DEVICE_KEY>' \
  --data-urlencode 'title=Codex' \
  --data-urlencode 'body=Finished' \
  --data-urlencode 'level=active' \
  --data-urlencode 'sound=bell'
```

### JSON POST to the public endpoint

```bash
curl --fail --silent --show-error \
  -X POST 'https://api.day.app/<DEVICE_KEY>' \
  -H 'Content-Type: application/json; charset=utf-8' \
  -d '{
    "title": "Codex",
    "body": "Finished",
    "level": "active",
    "sound": "bell",
    "group": "codex-learning"
  }'
```

### JSON POST to a self-hosted API v2 server

The official server's v2 route puts the key in the JSON body:

```bash
curl --fail --silent --show-error \
  -X POST 'https://<BARK_SERVER>/push' \
  -H 'Content-Type: application/json; charset=utf-8' \
  -d '{
    "device_key": "<DEVICE_KEY>",
    "title": "Codex",
    "body": "Finished",
    "level": "active",
    "sound": "bell",
    "group": "codex-learning"
  }'
```

## Common parameters

| Parameter | Meaning |
| --- | --- |
| `title` | Notification title |
| `subtitle` | Notification subtitle |
| `body` | Notification body |
| `level=active` | Normal immediate notification; default behavior |
| `level=timeSensitive` | Time-sensitive notification that can appear during Focus, subject to iOS permission/settings |
| `level=critical` | Critical alert; requires the user's iOS/Bark permission and should be reserved for genuinely critical events |
| `volume=0..10` | Critical-alert volume |
| `sound` | Bundled or custom sound name, without needing to show `.caf` in normal requests |
| `call=1` | Repeat the ringtone for 30 seconds; use only when explicitly requested |
| `group` | Group notifications in the notification center/history |
| `badge` | App icon badge number |
| `url` | URL or URL scheme opened when the notification is tapped |
| `icon` | Notification icon URL on supported iOS versions |
| `isArchive` | Control whether the message is kept in history |
| `ttl` | History retention duration in seconds |
| `id` | Stable id for updating an existing notification on supported versions |

## Response and latency

Treat a successful JSON response/HTTP 200 as “Bark accepted the request,” not as proof of APNs presentation. Measure sender-side latency separately:

```bash
curl -sS -o /dev/null \
  -w 'status=%{http_code} total=%{time_total}s\\n' \
  'https://api.day.app/<DEVICE_KEY>/Codex/Finished?level=active'
```

Do not log the full URL in a real integration because it contains the device key.
