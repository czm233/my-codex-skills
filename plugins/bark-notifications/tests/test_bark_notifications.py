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
    def test_diagnostics_rotation_and_write_failure_are_safe(self) -> None:
        hook = load_module("bark_diagnostics_test", BIN_ROOT / "bark-stop-hook")
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with mock.patch.dict(os.environ, {"CODEX_BARK_HOOK_STATE_DIR": temp,
                                              "CODEX_THREAD_ID": ""}):
                path = root / "diagnostics.jsonl"
                path.write_text("x" * 1_048_576)
                hook._record_diagnostic({}, "skipped", "empty_or_invalid_title")
                self.assertTrue((root / "diagnostics.jsonl.1").exists())
                record = json.loads(path.read_text())
                self.assertEqual(record["thread_relation"], "unavailable")
                with mock.patch.object(hook.os, "open", side_effect=OSError):
                    hook._record_diagnostic({}, "skipped", "test")

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

                (Path(codex_home) / "bark-notifications.json").write_text(
                    json.dumps({"sound": "bell_quiet"}), encoding="utf-8"
                )
                sender.os.environ["CODEX_BARK_MACHINE_LABEL"] = "Mini"
                sender.sys.stdin = io.StringIO("")
                self.assertEqual(sender.main(), 0)

        self.assertEqual(payloads[0]["title"], "Air (Lab)")
        self.assertEqual(payloads[0]["body"], "Session 含控制符")
        self.assertEqual(payloads[0]["group"], "codex-task-status:Air (Lab)")
        self.assertEqual(payloads[0]["sound"], "bell")
        self.assertEqual(payloads[1]["title"], "Mini")
        self.assertEqual(payloads[1]["body"], "本轮回复已结束")
        self.assertEqual(payloads[1]["group"], "codex-task-status:Mini")
        self.assertEqual(payloads[1]["sound"], "bell_quiet")

    def test_reply_preview_payload(self) -> None:
        sender = load_module("preview_sender", BIN_ROOT / "bark-task-complete")
        payloads = []
        def run(command, **kwargs):
            if command[0] == "/usr/bin/security":
                return subprocess.CompletedProcess(command, 0, stdout=b"placeholder")
            if command[0] == "/usr/bin/curl":
                payloads.append(json.loads(kwargs["input"]))
                return subprocess.CompletedProcess(command, 0, stdout=b"status=200")
            raise AssertionError("unexpected command")
        with mock.patch.object(sender, "resolve_machine_label", return_value="测试用户的完整电脑名称"), \
             mock.patch.object(sender, "resolve_sound", return_value="bell"), \
             mock.patch.object(sender.subprocess, "run", side_effect=run), \
             mock.patch.object(sender.sys, "argv", ["sender", "turn_stopped"]):
            for reply in ("短回复", "字" * 40, "换行\n测试\x00", ""):
                with mock.patch.object(sender.sys, "stdin", io.StringIO(json.dumps(
                    {"session_title": "会话标题", "reply_preview": reply}))):
                    self.assertEqual(sender.main(), 0)
        self.assertEqual(len(payloads), 3)
        self.assertEqual(payloads[0]["title"], "会话标题 · 测试用户的完整电脑名称")
        self.assertEqual(payloads[0]["body"], "短回复")
        self.assertEqual(payloads[1]["body"], "字" * 30 + "…")
        self.assertEqual(payloads[2]["body"], "换行 测试")
        self.assertEqual(payloads[0]["group"], "codex-task-status:测试用户的完整电脑名称")

    def test_invalid_sound_config_falls_back(self) -> None:
        sender = load_module("bark_sound_fallback_test", BIN_ROOT / "bark-task-complete")
        with tempfile.TemporaryDirectory(prefix="bark-sound-") as home:
            with mock.patch.dict(os.environ, {"CODEX_HOME": home}):
                path = Path(home) / "bark-notifications.json"
                for value in (None, {}, [], {"sound": ""}, {"sound": "../bell"},
                              {"sound": "bad\nname"}, {"sound": 1}, {"sound": "a" * 121}):
                    path.write_text(json.dumps(value), encoding="utf-8")
                    self.assertEqual(sender.resolve_sound(), "bell")
                path.write_text("{broken", encoding="utf-8")
                self.assertEqual(sender.resolve_sound(), "bell")

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
                "last_assistant_message": "回复测试",
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
            self.assertEqual(json.loads(captured_title.read_text(encoding="utf-8"))["session_title"], "Session 标题")

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

            # Metadata failures must not invoke the sender with a generic alert.
            fallback_event = {**event, "turn_id": "turn-fallback"}
            fallback_env = {
                **env,
                "CODEX_BARK_HOOK_CODEX_COMMAND": str(root / "missing-codex"),
            }
            self.assertEqual(invoke(fallback_event, fallback_env), "{}")
            self.assertEqual(
                json.loads(captured_title.read_text(encoding="utf-8"))["session_title"], "Session 标题"
            )

            records = [json.loads(line) for line in
                       (root / "state" / "diagnostics.jsonl").read_text().splitlines()]
            self.assertTrue(any(r["reason"] == "session_mismatch" and
                                r["thread_relation"] == "mismatch" for r in records))
            self.assertEqual(records[-1]["reason"], "process_start_failed")
            self.assertEqual(records[-1]["thread_relation"], "match")
            self.assertEqual(records[0]["outcome"], "sender_ok")
            serialized = json.dumps(records)
            for private in ("session-a", "internal-session", "Session 标题", str(root)):
                self.assertNotIn(private, serialized)
            self.assertEqual(stat.S_IMODE((root / "state" / "diagnostics.jsonl").stat().st_mode), 0o600)

            captured_title.unlink()
            self.assertEqual(invoke({**event, "turn_id": "missing-reply",
                                     "thread_name": "会话", "last_assistant_message": None}, env), "{}")
            self.assertFalse(captured_title.exists())
            self.assertEqual(json.loads((root / "state" / "diagnostics.jsonl").read_text().splitlines()[-1])["reason"], "missing_reply_preview")
            for title in (None, "", "本轮回复已结束", "本轮会话已结束"):
                self.assertEqual(invoke({**event, "turn_id": f"skip-{title}",
                                         "thread_name": title}, fallback_env), "{}")
                self.assertFalse(captured_title.exists())

            self.assertEqual(
                invoke({**event, "turn_id": "turn-active", "stop_hook_active": True}, env),
                "{}",
            )

    def test_stop_hook_accepts_zcode_style_event_without_turn_id(self) -> None:
        stop_hook = load_module("bark_stop_hook_zcode_test", BIN_ROOT / "bark-stop-hook")

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

        with tempfile.TemporaryDirectory(prefix="bark-stop-hook-zcode-test-") as temp_dir:
            root = Path(temp_dir)
            captured_title = root / "captured-title.txt"
            fake_sender = root / "fake-sender.py"
            fake_sender.write_text(
                "#!/usr/bin/env python3\n"
                "import os, pathlib, sys\n"
                "pathlib.Path(os.environ['CAPTURED_TITLE']).write_text(sys.stdin.read(), encoding='utf-8')\n",
                encoding="utf-8",
            )
            fake_sender.chmod(0o700)
            transcript = root / "transcript.jsonl"
            transcript.write_text("{}\n", encoding="utf-8")
            stop_hook.BARK_COMMAND = fake_sender

            # A ZCode-style Stop event omits hook_event_name and turn_id and
            # identifies the session through the transcript path.
            event = {
                "session_id": "zcode-session",
                "session_name": "测试会话",
                "last_assistant_message": "回复测试",
                "transcript_path": str(transcript),
                "cwd": str(root),
                "stop_hook_active": False,
            }
            env = {
                "CODEX_THREAD_ID": "",
                "CODEX_BARK_HOOK_CODEX_COMMAND": str(root / "missing-codex"),
                "CODEX_BARK_HOOK_STATE_DIR": str(root / "state"),
                "CAPTURED_TITLE": str(captured_title),
            }

            self.assertEqual(invoke(event, env), "{}")
            self.assertEqual(json.loads(captured_title.read_text(encoding="utf-8"))["session_title"], "测试会话")
            markers = list((root / "state").glob("*.sent"))
            self.assertEqual(len(markers), 1)

            # The same turn (identical transcript metadata) is deduplicated.
            self.assertEqual(invoke(event, env), "{}")
            self.assertEqual(len(list((root / "state").glob("*.sent"))), 1)

            # The next turn appends to the transcript, producing a new identity.
            with transcript.open("a", encoding="utf-8") as transcript_file:
                transcript_file.write("{}\n")
            self.assertEqual(invoke(event, env), "{}")
            self.assertEqual(len(list((root / "state").glob("*.sent"))), 2)

            # A session id is not required when a transcript path exists.
            self.assertEqual(
                invoke({**event, "session_id": ""}, env), "{}"
            )
            self.assertEqual(len(list((root / "state").glob("*.sent"))), 3)

            # An explicit non-Stop event name is still rejected.
            self.assertEqual(
                invoke({**event, "hook_event_name": "SubagentStop"}, env), "{}"
            )
            self.assertEqual(len(list((root / "state").glob("*.sent"))), 3)


if __name__ == "__main__":
    unittest.main()
