# my-codex-skills 技能安装脚本（Windows）
# 按 skills.sync.tsv 把仓库技能装到本机 DSH 技能根目录（优先 Junction：git pull 即生效；失败退回复制）。
# 用法：.\install.ps1 [-Force]
#   目标不存在               → 安装
#   目标已指向本仓           → 跳过（已是最新）
#   目标是普通目录且内容一致 → 替换
#   目标是普通目录且内容不同 → 跳过并警告（-Force 才覆盖；防止丢弃本机独立修改）
param([switch]$Force)

$ErrorActionPreference = "Stop"
$Repo = Split-Path -Parent $MyInvocation.MyCommand.Path

function DiffTrees([string]$a, [string]$b) {
	$ha = Get-ChildItem -Recurse -File $a | ForEach-Object {
		$_.FullName.Substring($a.Length + 1) + "|" + (Get-FileHash $_.FullName -Algorithm MD5).Hash
	} | Sort-Object
	$hb = Get-ChildItem -Recurse -File $b | ForEach-Object {
		$_.FullName.Substring($b.Length + 1) + "|" + (Get-FileHash $_.FullName -Algorithm MD5).Hash
	} | Sort-Object
	return -not (Compare-Object $ha $hb)
}

function RemoveLinkOrDir([string]$p) {
	# Junction/符号链接只删链接本身；普通目录递归删
	$item = Get-Item $p -Force
	if ($item.LinkType) { cmd /c rmdir /q "`"$p`"" } else { cmd /c rmdir /s /q "`"$p`"" }
	if (Test-Path $p) { throw "删除 $p 失败" }
}

$installed = 0; $skipped = 0; $warned = 0
Get-Content (Join-Path $Repo "skills.sync.tsv") | ForEach-Object {
	$line = $_.Trim()
	if ($line -eq "" -or $line.StartsWith("#")) { return }
	$parts = $line -split "`t"
	if ($parts.Count -lt 2) { throw "清单行格式错误：$line" }
	$name = $parts[0].Trim(); $root = $parts[1].Trim()
	switch ($root) {
		"dsh"    { $target = Join-Path $HOME ".dsh\skills\$name" }
		"agents" { $target = Join-Path $HOME ".agents\skills\$name" }
		default  { throw "未知根 $root（$name）" }
	}
	$src = Join-Path $Repo "skills\$name"
	if (-not (Test-Path $src)) { throw "仓库缺技能目录：$name" }
	$parent = Split-Path -Parent $target
	if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }

	if (Test-Path $target) {
		$item = Get-Item $target -Force
		if ($item.LinkType) {
			if ((Resolve-Path $target).Path -eq (Resolve-Path $src).Path) {
				Write-Host "＝ $name（已链接）"; $script:skipped++; return
			}
			Write-Host "！$name 链接指向别处，跳过"; $script:warned++; return
		}
		if (DiffTrees $src $target) {
			RemoveLinkOrDir $target
		} elseif ($Force) {
			Write-Host "！$name 本机有差异，-Force 覆盖"
			RemoveLinkOrDir $target
		} else {
			Write-Host "！$name 本机版本与仓库不同，跳过（确认后用 -Force 覆盖）"; $script:warned++; return
		}
	}

	$linked = $false
	cmd /c mklink /J "`"$target`"" "`"$src`"" > $null
	if ($LASTEXITCODE -eq 0) { $linked = $true }
	if ($linked) {
		Write-Host "＋ $name → $root（Junction）"
	} else {
		Copy-Item -Recurse -Path $src -Destination $target
		Write-Host "＋ $name → $root（复制）"
	}
	$script:installed++
}

Write-Host "完成：新装 $installed，已最新 $skipped，需人工确认 $warned"
