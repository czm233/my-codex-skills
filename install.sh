#!/usr/bin/env bash
# my-codex-skills 技能安装脚本（macOS/Linux）
# 按 skills.sync.tsv 把仓库技能装到本机 DSH 技能根目录（macOS 用符号链接：git pull 即生效）。
# 用法：./install.sh [--force]
#   目标不存在               → 安装
#   目标已是指向本仓的链接   → 跳过（已是最新）
#   目标是普通目录且内容一致 → 替换为链接
#   目标是普通目录且内容不同 → 跳过并警告（--force 才覆盖；防止丢弃本机独立修改）
set -euo pipefail

REPO="$(cd "$(dirname "$0")" && pwd)"
FORCE=0
[ "${1:-}" = "--force" ] && FORCE=1

line_ok() { [ -n "$1" ] && [ -n "$2" ]; }

installed=0; skipped=0; warned=0
while IFS=$'\t' read -r name root; do
	case "$name" in ''|'#'*) continue;; esac
	line_ok "$name" "$root" || { echo "× 清单行格式错误：$name|$root"; exit 1; }
	case "$root" in
		dsh)    target="$HOME/.dsh/skills/$name" ;;
		agents) target="$HOME/.agents/skills/$name" ;;
		*) echo "× 未知根 $root（$name）"; exit 1 ;;
	esac
	src="$REPO/skills/$name"
	[ -d "$src" ] || { echo "× 仓库缺技能目录：$name"; exit 1; }
	mkdir -p "$(dirname "$target")"

	if [ -L "$target" ]; then
		cur="$(readlink "$target")"
		if [ "$cur" = "$src" ]; then
			echo "＝ $name（已链接）"; skipped=$((skipped+1)); continue
		fi
		echo "！$name 链接指向别处（$cur），跳过"; warned=$((warned+1)); continue
	fi

	if [ -d "$target" ]; then
		if diff -rq "$src" "$target" >/dev/null 2>&1; then
			rm -rf "$target"
		elif [ "$FORCE" = 1 ]; then
			echo "！$name 本机有差异，--force 覆盖"
			rm -rf "$target"
		else
			echo "！$name 本机版本与仓库不同，跳过（确认后用 --force 覆盖）"; warned=$((warned+1)); continue
		fi
	fi

	ln -s "$src" "$target"
	echo "＋ $name → $root"; installed=$((installed+1))
done < "$REPO/skills.sync.tsv"

echo "完成：新装 $installed，已最新 $skipped，需人工确认 $warned"
