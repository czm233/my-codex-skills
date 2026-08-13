#!/usr/bin/env python3

"""No-network regression tests for the Bark plugin commands.

The same test file can exercise the repository checkout or an installed plugin
cache by setting ``BARK_TEST_PLUGIN_ROOT``.  It never reads the real Keychain
and replaces the Bark HTTP request with an in-process fake.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import stat
import subprocess
import tempfile
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock


PLUGIN_ROOT = Path(
    os.environ.get("BARK_TEST_PLUGIN_ROOT", str(Path(__file__).resolve().parents[1]))
).resolve()
SKILL_ROOT = PLUGIN_ROOT / "skills" / "bark-notifications"
BIN_ROOT = SKILL_ROOT / "bin"


def load_module(name: str, path: Path):
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BarkPluginTests(unittest.TestCase):
    def test_sender_payload_uses_machine_label_and_session_title(self) -> None:
        sender = load_module(
            "bark_task_complete_test", BIN_ROOT / "bark-task-complete"
        )
        payloads: list[dict[str, object]] = []

        def fake_run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
            if command[:2] == ["/usr/bin/security", "find-generic-password"]:
                return subprocess.CompletedProcess(command, 0, stdout=b"placeholder")
            if command and command[0] == "/usr/bin/curl":
                payloads.append(json.loads(kwargs["input"].decode("utf-8")))
                return subprocess.CompletedProcess(
                    command, 0, stdout=b"status=200 total=0.01s"
                )
            raise AssertionError(f"unexpected subprocess: {command}")

        with tempfile.TemporaryDirectory(prefix="bark-sender-test-") as codex_home:
            with (
                mock.patch.dict(
                    os.environ,
                    {
                        "CODEX_HOME": codex_home,
                        "CODEX_BARK_MACHINE_LABEL": "Air\n[Lab]",
                    },
                    clear=False,
                ),
                mock.patch.object(sender.subprocess, "run", side_effect=fake_run),
                mock.patch.object(
                    sender.sys,
                    "argv",
                    ["bark-task-complete", "turn_stopped"],
                ),
                mock.patch.object(
                    sender.sys,
                    "stdin",
                    io.StringIO("Session\n含控制符\x00"),
                ),
            ):
                self.assertEqual(sender.main(), 0)

                sender.os.environ["CODEX_BARK_MACHINE_LABEL"] = "Mini"
                sender.sys.stdin = io.StringIO("")
                self.assertEqual(sender.main(), 0)

        self.assertEqual(payloads[0]["title"], "Air (Lab)")
        self.assertEqual(payloads[0]["body"], "Session 含控制符")
        self.assertEqual(payloads[0]["group"], "codex-task-status:Air (Lab)")
        self.assertEqual(payloads[1]["title"], "Mini")
        self.assertEqual(payloads[1]["body"], "本轮回复已结束")
        self.assertEqual(payloads[1]["group"], "codex-task-status:Mini")

    def test_machine_config_isolated_and_protected_from_silent_overwrite(self) -> None:
        configurer = load_module(
            "bark_configure_machine_test", BIN_ROOT / "bark-configure-machine"
        )

        with tempfile.TemporaryDirectory(prefix="bark-machine-config-test-") as codex_home:
            with mock.patch.dict(os.environ, {"CODEX_HOME": codex_home}, clear=False):
                with mock.patch.object(
                    configurer.sys,
                    "argv",
                    ["bark-configure-machine", "--machine-label", "Lab\nAir"],
                ):
                    self.assertEqual(configurer.main(), 0)

                config_path = Path(codex_home) / "bark-notifications.json"
                self.assertEqual(
                    json.loads(config_path.read_text(encoding="utf-8"))["machine_label"],
                    "Lab Air",
                )
                self.assertEqual(stat.S_IMODE(config_path.stat().st_mode), 0o600)

                with mock.patch.object(
                    configurer.sys,
                    "argv",
                    ["bark-configure-machine", "--machine-label", "Other"],
                ):
                    self.assertEqual(configurer.main(), 73)

    def test_stop_hook_reads_only_thread_metadata_and_deduplicates(self) -> None:
        stop_hook = load_module("bark_stop_hook_test", BIN_ROOT / "bark-stop-hook")

        def invoke(event: dict[str, object], env: dict[str, str]) -> str:
            output = io.StringIO()
            with (
                mock.patch.dict(os.environ, env, clear=False),
                mock.patch.object(
                    stop_hook.sys,
                    "stdin",
                    io.StringIO(json.dumps(event, ensure_ascii=False)),
                ),
                contextlib.redirect_stdout(output),
            ):
                self.assertEqual(stop_hook.main(), 0)
            return output.getvalue()

        with tempfile.TemporaryDirectory(prefix="bark-stop-hook-test-") as temp_dir:
            root = Path(temp_dir)
            captured_title = root / "captured-title.txt"
            protocol_log = root / "protocol.jsonl"
            fake_sender = root / "fake-sender.py"
            fake_sender.write_text(
                "#!/usr/bin/env python3\n"
                "import os, pathlib, sys\n"
                "pathlib.Path(os.environ['CAPTURED_TITLE']).write_text(sys.stdin.read(), encoding='utf-8')\n",
                encoding="utf-8",
            )
            fake_sender.chmod(0o700)

            fake_codex = root / "fake-codex.py"
            fake_codex.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, sys\n"
                "from pathlib import Path\n"
                "log = Path(os.environ['PROTOCOL_LOG'])\n"
                "for line in sys.stdin:\n"
                "    message = json.loads(line)\n"
                "    with log.open('a', encoding='utf-8') as output:\n"
                "        output.write(json.dumps(message, ensure_ascii=False) + '\\n')\n"
                "    if message.get('id') == 1:\n"
                "        print(json.dumps({'id': 1, 'result': {}}), flush=True)\n"
                "    elif message.get('id') == 2:\n"
                "        print(json.dumps({'id': 2, 'result': {'thread': {'name': '  Session\\n标题\\x00  '}}}, ensure_ascii=False), flush=True)\n",
                encoding="utf-8",
            )
            fake_codex.chmod(0o700)

            stop_hook.BARK_COMMAND = fake_sender
            event = {
                "hook_event_name": "Stop",
                "session_id": "session-a",
                "turn_id": "turn-1",
                "stop_hook_active": False,
            }
            env = {
                "CODEX_THREAD_ID": "session-a",
                "CODEX_BARK_HOOK_CODEX_COMMAND": str(fake_codex),
                "CODEX_BARK_HOOK_STATE_DIR": str(root / "state"),
                "CAPTURED_TITLE": str(captured_title),
                "PROTOCOL_LOG": str(protocol_log),
            }

            self.assertEqual(invoke(event, env), "{}")
            self.assertEqual(captured_title.read_text(encoding="utf-8"), "Session 标题")

            requests = [
                json.loads(line)
                for line in protocol_log.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(
                [request.get("method") for request in requests],
                ["initialize", "initialized", "thread/read"],
            )
            self.assertEqual(requests[-1]["params"], {"threadId": "session-a", "includeTurns": False})
            self.assertNotIn("transcript_path", requests[-1])

            # The same event is a no-op, and an internal session is filtered before
            # it creates a marker or invokes the sender.
            self.assertEqual(invoke(event, env), "{}")
            self.assertEqual(len(list((root / "state").glob("*.sent"))), 1)
            self.assertEqual(
                invoke(
                    {
                        **event,
                        "session_id": "internal-session",
                        "turn_id": "internal-turn",
                    },
                    env,
                ),
                "{}",
            )
            self.assertEqual(len(list((root / "state").glob("*.sent"))), 1)

            # If metadata is unavailable, the notification still completes with
            # the fixed safe fallback and no hook continuation.
            fallback_event = {**event, "turn_id": "turn-fallback"}
            fallback_env = {
                **env,
                "CODEX_BARK_HOOK_CODEX_COMMAND": str(root / "missing-codex"),
            }
            self.assertEqual(invoke(fallback_event, fallback_env), "{}")
            self.assertEqual(
                captured_title.read_text(encoding="utf-8"), "本轮回复已结束"
            )

            self.assertEqual(
                invoke({**event, "turn_id": "turn-active", "stop_hook_active": True}, env),
                "{}",
            )


if __name__ == "__main__":
    unittest.main()
