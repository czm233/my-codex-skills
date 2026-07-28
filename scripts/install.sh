#!/usr/bin/env bash

set -euo pipefail

force=false
if [[ "${1:-}" == "--force" ]]; then
  force=true
elif [[ $# -gt 0 ]]; then
  echo "Usage: $0 [--force]" >&2
  exit 2
fi

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_dir="$(cd "${script_dir}/.." && pwd)"
source_dir="${repo_dir}/skills"
codex_dir="${CODEX_HOME:-${HOME}/.codex}"
target_dir="${codex_dir}/skills"

mkdir -p "${target_dir}"

installed=0
for skill_file in "${source_dir}"/*/SKILL.md; do
  [[ -e "${skill_file}" ]] || continue

  skill_dir="$(dirname "${skill_file}")"
  skill_name="$(basename "${skill_dir}")"
  target_path="${target_dir}/${skill_name}"

  if [[ -L "${target_path}" ]] && [[ "$(readlink "${target_path}")" == "${skill_dir}" ]]; then
    echo "up to date: ${skill_name}"
    installed=$((installed + 1))
    continue
  fi

  if [[ -e "${target_path}" || -L "${target_path}" ]]; then
    if [[ "${force}" != true ]]; then
      echo "conflict: ${target_path} already exists (use --force to replace it)" >&2
      exit 1
    fi
    rm -rf -- "${target_path}"
  fi

  ln -s "${skill_dir}" "${target_path}"
  echo "installed: ${skill_name}"
  installed=$((installed + 1))
done

if [[ ${installed} -eq 0 ]]; then
  echo "No skills found under ${source_dir}."
else
  echo "Installed ${installed} skill(s) into ${target_dir}."
fi
