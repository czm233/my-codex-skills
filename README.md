# my-codex-skills

用于集中版本控制、持续改进并在多台电脑之间同步个人 Codex Skills。

## 仓库结构

```text
my-codex-skills/
├── skills/                 # 正式技能；每个子目录都是一个独立 Skill
│   └── <skill-name>/
│       └── SKILL.md
├── templates/
│   └── skill-template/     # 新技能模板
└── scripts/
    └── install.sh          # 安装/同步到本机 Codex
```

## 新建一个 Skill

```bash
cp -R templates/skill-template skills/my-new-skill
```

然后编辑 `skills/my-new-skill/SKILL.md`。建议一个技能只解决一类清晰的问题；需要的脚本、参考资料和资源都放在该技能自己的目录内。

## 在当前电脑安装

默认把仓库中的每个技能链接到 `~/.codex/skills/`：

```bash
./scripts/install.sh
```

符号链接适合开发：修改仓库里的 Skill 后，Codex 会直接使用最新内容。

如果目标位置已经存在同名文件或目录，脚本会停止且不会覆盖。确认旧内容可以替换后，可以显式执行：

```bash
./scripts/install.sh --force
```

## 在其他电脑同步

```bash
git clone https://github.com/czm233/my-codex-skills.git
cd my-codex-skills
./scripts/install.sh
```

以后更新只需：

```bash
git pull --ff-only
./scripts/install.sh
```

## 安全约定

- 不提交 API Key、Token、Cookie、密码、私钥或其他真实凭证。
- 本机配置使用 `.env.local`、`config.local.*` 等文件，并保持在 Git 忽略列表中。
- 需要展示配置格式时，只提交带明显占位值的 `.example` 或 `.sample` 文件。

## 推荐迭代流程

1. 在独立技能目录中修改并本机验证。
2. 检查 Git diff，确认没有凭证和本机敏感配置。
3. 提交并推送到 GitHub。
4. 其他电脑拉取最新版本。
