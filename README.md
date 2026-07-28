# my-codex-skills

用于集中版本控制、持续改进并在多台电脑之间同步个人 Codex Skills。

## 仓库结构

```text
my-codex-skills/
├── skills/                 # 正式技能；每个子目录都是一个独立 Skill
│   ├── check/              # 开发前分析与开发后复盘
│   └── simple/             # 把复杂内容解释清楚并生成配套图表
└── templates/
    └── skill-template/     # 新技能模板
```

## 已收录 Skills

| Skill | 用途 | 安装路径 |
|---|---|---|
| `check` | 开发前分析根因并对比方案；开发后复盘修改前后差异 | `skills/check` |
| `simple` | 用易懂中文、流程图、时序图和对照表解释复杂内容 | `skills/simple` |

## 新建一个 Skill

```bash
cp -R templates/skill-template skills/my-new-skill
```

然后编辑 `skills/my-new-skill/SKILL.md`。建议一个技能只解决一类清晰的问题；需要的脚本、参考资料和资源都放在该技能自己的目录内。

## 在当前电脑安装

使用 Codex 内置的 `$skill-installer`，按需安装指定 Skill。例如：

```text
使用 $skill-installer 从 czm233/my-codex-skills 安装：
skills/check
skills/simple
```

也可以一次指定多个 Skill：

```text
使用 $skill-installer 从 czm233/my-codex-skills 安装：
skills/skill-one
skills/skill-two
```

## 在其他电脑同步

在目标电脑登录有权访问该仓库的 GitHub 账号，然后通过 `$skill-installer` 安装需要的 Skill。

`$skill-installer` 默认不会覆盖已存在的同名 Skill。需要更新时，让 Codex 删除本机旧版本并从仓库重新安装指定 Skill：

```text
使用 $skill-installer 重新安装 czm233/my-codex-skills 中的：
skills/check
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
