# RepoStew

**简体中文** | [English](README.en.md)

RepoStew 是一个可移植的 [Agent Skill](https://agentskills.io/)，用于负责任地维护 GitHub 仓库。它帮助编码智能体发现和评估 issue、审计仓库、实现聚焦修复、验证改动、提交 Pull Request，并持续处理审查意见和 CI。

RepoStew 与具体智能体和操作系统无关。核心工作流位于 `SKILL.md`，Python 脚本提供可选的确定性发现、状态跟踪和安全清理能力。Skill 不依赖特定模型供应商、GitHub 用户名、工作区路径或 shell。

## RepoStew 能做什么

- 在确认 issue 仍可处理后修复指定 GitHub issue。
- 扫描单个仓库，寻找任意复杂度的高价值贡献候选。
- 在 GitHub 上发现合适的 issue，并机械检查重复项和认领状态。
- 全面审计仓库，起草有证据、非重复的 issue。
- 遵循目标仓库规则，创建最小且经过测试的改动。
- 在确认模式或自主模式下提交并跟踪 Pull Request。
- 持久保存未处理的 PR 评论和 review，继续完成代码修改、回复、CI 修复和冲突处理。
- 维护已验证具有 `owner`、`admin` 或 `maintain` 权限的仓库，不在每次事件中重复外部贡献者资格检查。
- 保存贡献记录，并跟进曾参与仓库中新开的 issue。
- 盘点并安全清理显式登记、且关联 PR 已合并或关闭的本地 worktree 和分支。
- 在当前对话中完成简单、局部的问题；在宿主支持时，将复杂或长期工作交接到单独的用户可见任务。
- 在真实使用暴露陈旧、不安全、损坏或不可移植的行为时维护 RepoStew 自身。

## 支持的智能体

RepoStew 遵循开放的 `SKILL.md` 格式。同一目录可用于实现 Agent Skills 标准的智能体。

| 智能体 | 项目级目录 | 用户级目录 | 调用方式 |
|---|---|---|---|
| OpenAI Codex | `.agents/skills/repostew` | `~/.agents/skills/repostew` | 提及 `$repostew`，或由 Codex 根据描述自动匹配 |
| Cursor | `.agents/skills/repostew` 或 `.cursor/skills/repostew` | `~/.agents/skills/repostew` 或 `~/.cursor/skills/repostew` | `/repostew` 或自动调用 |
| Gemini CLI | `.agents/skills/repostew` 或 `.gemini/skills/repostew` | `~/.agents/skills/repostew` 或 `~/.gemini/skills/repostew` | 自动调用或使用 Gemini skills 命令 |
| GitHub Copilot | `.agents/skills/repostew` 或 `.github/skills/repostew` | `~/.agents/skills/repostew` 或 `~/.copilot/skills/repostew` | `/repostew` 或自动调用 |
| Claude Code | `.claude/skills/repostew` | `~/.claude/skills/repostew` | `/repostew` 或自动调用 |

对于 Codex、Cursor、Gemini CLI 和 GitHub Copilot，推荐使用共享目录 `.agents/skills`。Claude Code 当前使用 `.claude/skills`。

平台文档：[Codex skills](https://learn.chatgpt.com/docs/build-skills)、[Claude Code skills](https://code.claude.com/docs/en/skills)、[Cursor skills](https://cursor.com/docs/skills)、[Gemini CLI skills](https://geminicli.com/docs/cli/skills/) 和 [GitHub Copilot skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)。

## 前置条件

- Git
- Python 3.10 或更高版本
- 已使用贡献账号登录的 [GitHub CLI](https://cli.github.com/)
- 兼容 Agent Skills 的编码智能体

验证命令行环境：

```bash
git --version
python --version
gh auth status
```

如果系统用 `python3` 表示 Python 3，请将示例中的 `python` 替换为 `python3`。

## 安装

始终克隆到名为 `repostew` 的目录；目录名必须与 skill 的 `name` 一致。

### 推荐：为单个仓库安装

这种方式让 RepoStew 与目标工作区一起版本化，并只在该工作区生效。

macOS/Linux：

```bash
mkdir -p .agents/skills
git clone https://github.com/dajiaohuang/RepoStew_skills.git .agents/skills/repostew
```

Windows PowerShell：

```powershell
New-Item -ItemType Directory -Force -Path ".agents\skills" | Out-Null
git clone https://github.com/dajiaohuang/RepoStew_skills.git ".agents\skills\repostew"
```

这个项目级安装可被 Codex、Cursor、Gemini CLI 和 GitHub Copilot 发现。Claude Code 请将上述路径中的 `.agents/skills/repostew` 换成 `.claude/skills/repostew`。

macOS/Linux：

```bash
mkdir -p .claude/skills
git clone https://github.com/dajiaohuang/RepoStew_skills.git .claude/skills/repostew
```

Windows PowerShell：

```powershell
New-Item -ItemType Directory -Force -Path ".claude\skills" | Out-Null
git clone https://github.com/dajiaohuang/RepoStew_skills.git ".claude\skills\repostew"
```

### 为当前用户安装

Codex、Cursor、Gemini CLI 和 GitHub Copilot 可共用用户级目录。

macOS/Linux：

```bash
mkdir -p ~/.agents/skills
git clone https://github.com/dajiaohuang/RepoStew_skills.git ~/.agents/skills/repostew
```

Windows PowerShell：

```powershell
New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.agents\skills" | Out-Null
git clone https://github.com/dajiaohuang/RepoStew_skills.git "$env:USERPROFILE\.agents\skills\repostew"
```

Claude Code 请把命令中的 `.agents` 替换为 `.claude`。

### 使用 Gemini CLI 安装器

Gemini CLI 也可以直接安装仓库：

```bash
gemini skills install https://github.com/dajiaohuang/RepoStew_skills.git
```

添加 `--scope workspace` 可安装到当前工作区。启用前应先审查任何第三方 skill。

### 更新现有安装

项目级安装：

```bash
git -C .agents/skills/repostew pull --ff-only
```

macOS/Linux 用户级安装：

```bash
git -C ~/.agents/skills/repostew pull --ff-only
```

Windows PowerShell 用户级安装：

```powershell
git -C "$env:USERPROFILE\.agents\skills\repostew" pull --ff-only
```

如果使用平台专属目录，请替换为实际安装路径。更新后若智能体未检测到变化，请重新加载或重启其 skill 列表。

## 使用 RepoStew

示例：

```text
使用 RepoStew 修复 https://github.com/owner/repo/issues/42
使用 RepoStew 扫描 owner/repo，找一个值得修复的小 issue
使用 RepoStew 全面审计 owner/repo，并起草已确认的 bug 报告
使用 RepoStew 为我寻找 3 个范围清晰的开源 issue
使用 RepoStew 检查并维护我跟踪的 Pull Request
使用 RepoStew 维护我已验证拥有或管理的仓库
使用 RepoStew 自主运行，连续 3 轮没有候选后停止
```

### 确认模式

确认模式是默认模式：

```text
只读调查 → 展示候选或计划 → 用户批准编辑 → 实现并测试
→ 用户批准外部提交 → 创建 issue 或 PR → 跟踪
```

只读调查可以立即执行；代码编辑和 GitHub 外部写操作需要等待确认。

### 自主模式

用户明确使用 `autonomous`、`automatic`、`continuous`、`no confirmation`、`自动` 或 `持续` 等词时启用自主模式：

```text
发现 → 评估 → 核验 → 修复 → 测试 → 提交 → PR → 跟踪 → 维护
```

自主模式只取消已授权范围内的中间确认。它不会授予维护者权限、绕过仓库政策、自动批准新依赖或服务，也不会关闭宿主智能体的安全控制。连续三轮扩大范围后仍没有可处理候选时，RepoStew 会停止。

## 贡献质量门槛

RepoStew 使用三个内部决策：

| 决策 | 含义 |
|---|---|
| `ACCEPT` | 清晰、允许、兼容、可测试、有价值并符合仓库方向；复杂度只决定执行路径 |
| `ASK_MAINTAINER` | 应用直接 PR 判断门槛后，仍有需求、API、架构、依赖、服务、安全、权限或兼容性决定需要维护者批准 |
| `SKIP` | 重复、已分配、已修复、被政策禁止、纯推测、无法验证，或缺少必要访问权限 |

标签只是发现信号，不代表许可。每个候选都需要检查 issue 讨论、提交、打开和关闭的 PR、关联 closing PR、仓库说明、贡献政策和长期维护成本。

核验完成后，RepoStew 再按执行复杂度分流。清晰且局部的改动留在当前对话；跨子系统工作、全仓库审计、多 issue 活动和长期维护，在平台支持时使用单独的用户可见任务或交接。复杂本身不构成拒绝理由。交接必须包含证据和权限边界，而接收任务会重新检查 GitHub 当前状态。

RepoStew 不把提问或 Draft PR 当作常规前置步骤。自主模式下，当仓库接受外部 PR、issue 仍开放且无人处理、行为可从 issue/测试/代码模式可靠推断、方案最小且保持兼容、没有跨越需审批的依赖/服务/权限/CI/安全/公共 API/架构边界、聚焦验证通过且 PR 如实记录假设时，RepoStew 会直接提交普通 PR。

如果应用上述门槛后仍确实需要维护者决策，RepoStew 获得一次在现有公开 issue、discussion 或贡献者自己的 PR 上发布聚焦澄清评论的权限。它会先确认问题没有已有答案，说明阻塞决策和选项，保存评论 URL，然后等待且不重复催促。该例外不授权创建新 issue/discussion、认领工作、承诺交付或公开安全敏感信息。

### 直接 PR 与受权限约束的 Draft PR

RepoStew 将“允许提交 PR”与“技术方向已获批准”分开判断。普通 PR 是通过直接 PR 门槛后的默认选择；仍有实质实现不确定性时，才使用 Draft 展示假设和替代方案。

| 仓库政策 | RepoStew 的动作 |
|---|---|
| 接受未经邀请的 PR 或早期 Draft，但尚未达到普通 PR 门槛 | 创建一个聚焦的上游 Draft PR，标明未决问题，不使用 closing keyword，等待方向确认 |
| 外部 PR 仅限邀请、提交前必须批准，或要求先就方案达成一致 | 不用 Draft 绕过政策；推送到 fork 分支并创建 fork 内 Draft。平台不支持时，保留已测试分支和完整 PR 草稿，只在现有讨论中请求一次邀请 |
| 当前阶段明确禁止实现或公开原型，或改动跨越安全、依赖、服务、凭据、特权权限或公共 API 门槛 | 只保留设计草稿或本地实现，并引用明确禁止条款 |

对于仅限邀请的项目，公开说明可以写成：

> 贡献政策说明外部 PR 仅限受邀提交，因此我没有创建上游 PR。我准备了一个经过测试的草稿：`<draft URL or fork branch>`。如果这个方向符合项目架构，获得邀请后我可以按项目的正常审查流程提交。

Draft 是审查材料，不代表认领、批准或合并权限。RepoStew 会保存草稿和讨论 URL，等待且不刷屏；提交上游前重新检查政策、认领状态、竞争 PR 和默认分支。

## 仓库审计工作流

RepoStew 既能生成补丁，也能生成 issue。只有完成以下步骤后才会提交报告：

1. 复现问题或收集充分的源码证据；
2. 检查受支持版本和默认分支；
3. 搜索已有 issue、discussion、PR 和提交；
4. 最小化复现；
5. 将已确认缺陷与偏好或推测性改进分开；
6. 遵循仓库 issue 模板和安全报告政策。

确认模式会在发布前展示 issue 标题和正文草稿。RepoStew 不会批量提交低置信度发现。

## 内置脚本

脚本只使用 Python 标准库以及外部 `git`/`gh` 命令。

| 脚本 | 用途 |
|---|---|
| `scripts/discover.py` | 通过全局、方向性和直接搜索排列活跃仓库或发现 issue 候选 |
| `scripts/contribution_tracker.py` | 持久保存参与过的仓库、PR 和 issue |
| `scripts/scan_known_repos.py` | 在参与过的仓库中寻找新的 issue 候选 |
| `scripts/pr_tracker.py` | 持久保存 PR 状态、CI、review、评论和未处理活动 |
| `scripts/maintained_repositories.py` | 验证独立的 owner/maintainer 权限登记表 |
| `scripts/workspace_cleanup.py` | 以 dry-run 优先方式清理已验证终态 PR 的 worktree 和本地分支 |
| `scripts/loop.py` | 执行有界、逐步扩大的发现轮次 |
| `scripts/auto_fix.py` | 可选的供应商无关调度器，调用用户指定的非交互智能体命令 |
| `scripts/auto_fix.sh` | `auto_fix.py` 的轻量 POSIX 包装脚本 |

### 发现候选

```bash
# 最近活跃的仓库
python scripts/discover.py --min-stars 100 --max-days 7 --repo-count 10

# 某个技术方向中活跃的高 star 仓库
python scripts/discover.py --repos-only --min-stars 100 --max-days 30 \
  --focus agentic --focus "agent framework" --focus "agent harness" --focus nanobot

# 使用全部发现策略
python scripts/discover.py \
  --direct --keyword --kw-min-stars 5 --max-days 120 --max-candidates 5

# 隐藏进度日志，只输出 JSON
python scripts/discover.py --direct --json-only
```

`--focus` 可重复使用，以多个相关搜索词和可选的代表性项目名表达一个宽泛方向。每个查询先贡献自己的最佳匹配，再按 star 合并排序，避免最宽泛的词挤掉相邻领域。`--min-stars` 和 `--kw-min-stars` 只设下限；RepoStew 不设 star 上限。

使用 `--repos-only` 可先定位仓库，再寻找 issue。提供 `--focus` 时，发现范围限制在匹配仓库内，不会混入无关的宽泛直接 issue 流。输出只是候选清单，仍需人工或智能体核验主题相关性、仓库健康度、贡献政策和具体 issue。

### PR 跟踪

```bash
# 首次使用时导入当前 GitHub 账号可访问的 PR 历史
python scripts/pr_tracker.py import-authored

python scripts/pr_tracker.py add \
  "https://github.com/owner/repo/pull/123" \
  "https://github.com/owner/repo/issues/42"

python scripts/pr_tracker.py notifications
python scripts/pr_tracker.py list
python scripts/pr_tracker.py check  # 低频开放 PR 对账
```

评论跟进以通知为主。GitHub Notifications 选择需要完整刷新状态、CI、review、普通评论和 inline 评论的已跟踪 PR：

```bash
python scripts/pr_tracker.py notifications
python scripts/pr_tracker.py notifications --repo owner/repo
```

该命令使用持久时间戳 checkpoint，而不是 unread 状态。它请求上次成功批次后、当前贡献者参与或被提及的通知，保存到通用 notification inbox，并保持 GitHub 已读状态不变。因此即使用户自行阅读通知，流程仍可靠；Issue 或尚未跟踪的 PR 事件也不会丢失。

如果智能体平台可以读取 Outlook，可把用户已配置的 Outlook 文件夹作为 GitHub Notifications 不可用时的备用来源。RepoStew 仍会回到 GitHub 核验每个事件。每个来源只有在整个批次已处理或持久保留后，才将 checkpoint 推进到批次开始时间。更宽泛的 `check` 只作为低频防漏机制。

```bash
python scripts/pr_tracker.py notification-inbox
python scripts/pr_tracker.py notification-resolve <thread-id>
```

外部活动在贡献者读完、完成并测试必要修改、推送现有分支并回复前一直保持 pending。之后再解析当前活动集：

```bash
python scripts/pr_tracker.py resolve \
  "https://github.com/owner/repo/pull/123"
python scripts/pr_tracker.py notifications --repo owner/repo
```

### 持久贡献跟进

PR 会自动登记。主动维护的仓库和提交过的 issue 可手动加入：

```bash
python scripts/contribution_tracker.py add \
  "https://github.com/owner/repo/issues/84"
python scripts/contribution_tracker.py add \
  "https://github.com/owner/repo"
python scripts/contribution_tracker.py list
```

扫描持久仓库集合或指定仓库中新开的 issue：

```bash
python scripts/scan_known_repos.py
python scripts/scan_known_repos.py --repo owner/repo
python scripts/scan_known_repos.py --repo owner/one --repo owner/two
python scripts/scan_known_repos.py --since-days 30 --issue-limit 50
python scripts/scan_known_repos.py --repo owner/repo --include-decisions
```

`--repo` 可以重复。维护工作区有明确 active-follow 表时，应传入显式集合，避免历史贡献把已暂停仓库重新加入例行维护。

扫描器以一天重叠保存最后一次成功扫描。每次运行都会按仓库报告候选、过滤项、已见 issue、详情获取失败和截断状态；`--include-decisions` 会为每个列出的 issue 输出机械过滤原因。详情获取失败或结果超过 `--issue-limit` 时不推进该仓库 checkpoint，以便重试。输出仍需经过政策、重复项、分配、关联 PR、相关性和范围检查。过去参与过仓库不代表获得维护权限，也不能成为提交低置信度 issue 的理由。

### 自有和受维护仓库

持久工作区将“接收范围”和“权限”保存在不同文件中：

- `FOLLOWED_REPOSITORIES.md` 选择例行事件中的 `active`/`self` 仓库；
- `MAINTAINED_REPOSITORIES.md` 保存已验证的 `owner`、`admin` 或 `maintain` 权限。

关注或贡献过仓库不代表拥有权限；拥有权限本身也不会把仓库加入定时接收范围。

验证权限表：

```bash
python scripts/maintained_repositories.py MAINTAINED_REPOSITORIES.md
```

对于启用且近期验证过的记录，RepoStew 在维护用户自己的 PR 和分支时，可以不在每次通知中重复检查外部贡献者资格、CLA 是否适用、仓库是否接受 PR 或是否具备 push 权限。它仍会在通知或状态变化时刷新一次完整 PR 快照、遵循仓库说明、运行必要验证并维持 checkpoint 规则。

该权限表不授权自动合并或关闭、删除远端内容、修改治理、发布版本或访问 secret。详见 [`references/maintaining-owned-repositories.md`](references/maintaining-owned-repositories.md)。

### 安全清理本地工作区

从 linked worktree 提交并跟踪 PR 后，应显式登记本地资源，避免将来通过目录名或分支名猜测所有权：

```bash
python scripts/workspace_cleanup.py register \
  --workspace /absolute/path/to/workspace \
  --worktree /absolute/path/to/workspace/repo-issue \
  --pr-url https://github.com/owner/repo/pull/123
```

如果同一个 PR 分支随后经过 rebase、amend 或 force-push，应先刷新 PR tracker 并推送新 tip，再显式更新原所有权记录：

```bash
python scripts/workspace_cleanup.py rebind \
  --workspace /absolute/path/to/workspace \
  --worktree /absolute/path/to/workspace/repo-issue \
  --pr-url https://github.com/owner/repo/pull/123
```

`rebind` 不能转移 worktree、分支、仓库或 PR；它只会在重新核验同一 PR 和已推送 tip 后更新 commit，并把旧、新 commit 保留在历史中。

不带 `--apply` 时，清理只执行 dry run：

```bash
python scripts/workspace_cleanup.py cleanup --workspace /absolute/path/to/workspace
python scripts/workspace_cleanup.py cleanup --workspace /absolute/path/to/workspace --apply --json
```

只有显式登记、且跟踪 PR 为 `MERGED` 或 `CLOSED` 的 linked worktree 才可能符合条件。RepoStew 会在删除前再次核验精确路径、canonical clone 边界、分支、GitHub remote 身份、已推送 tip、tracked/untracked 状态、ignored 输出和 worktree 所有权。

Canonical clone、fork、远端分支、活动 PR、凭据、未知 ignored 数据以及未提交或未推送的工作始终不受影响。JSON 结果同时报告估算和实际释放的逻辑字节数，`workspace_resources.json` 保留所有权与清理历史。详见 [`references/workspace-cleanup.md`](references/workspace-cleanup.md)。

### 定时维护示例

[`references/scheduled-maintenance.md`](references/scheduled-maintenance.md) 提供可复制、平台无关的定时任务提示词，包括每两小时运行的 notification-first 维护 inbox，以及每周一次的安全存储清理。示例均使用持久 checkpoint、最小权限和有界独立运行。

全面仓库审计和审计驱动的主动 issue 提交被明确排除在定时任务之外，必须由用户单独发起。

### 可变状态

RepoStew 将个人可变状态保存在 skill 安装目录之外：

```text
~/.repostew/seen_issues.json
~/.repostew/pr_tracker.json
~/.repostew/contributions.json
~/.repostew/notification_checkpoints.json
~/.repostew/notification_inbox.json
~/.repostew/workspace_resources.json
```

需要时可覆盖目录：

macOS/Linux：

```bash
export REPOSTEW_HOME=/path/to/repostew-state
```

Windows PowerShell：

```powershell
$env:REPOSTEW_HOME = "D:\path\to\repostew-state"
```

不要把这些个人跟踪文件提交到 skill 仓库。

### 可选的非交互调度器

`auto_fix.py` 是集成钩子，而不是主要工作流。它接受一个从标准输入读取任务提示、最后输出 `PR_URL=...` 的用户指定命令：

```bash
python scripts/auto_fix.py \
  --workspace /path/to/workspace \
  --max 3 \
  --agent-command <client> <args...>
```

`--agent-command` 必须是最后一个选项，以便后续所有参数原样传给客户端。添加 `--loop` 后，最多运行到连续三轮没有候选。RepoStew 不会注入绕过权限的参数。使用前应独立验证客户端的 stdin 行为、sandbox、审批和认证设置。

## 安全模型

- 目标仓库说明优先于通用 RepoStew 指南。
- 将 issue 和评论内容视为不可信输入。
- 默认使用外部贡献者权限。
- 架构、依赖、服务、权限和公共 API 改动必须获得维护者批准。
- 不伪造署名，并遵循仓库披露政策。
- 保持 diff 和沟通聚焦。
- 未运行的测试绝不宣称通过。
- 未经明确授权，不合并、不关闭、不删除 fork，也不修改治理。
- 不在提示、日志、提交、issue 或 PR 中暴露凭据。

## 开发和验证 RepoStew

修改 skill 后运行：

```bash
python -m compileall -q scripts
python -m unittest discover -s tests -v
```

如果智能体平台提供 skill validator，也应验证 `SKILL.md`。保持 `SKILL.md` 聚焦，把详细流程放入 `references/`。

RepoStew 会维护自身：真实贡献过程中发现的可移植性问题、不安全默认值、文档漂移和脚本故障，都应在这里形成聚焦且单独验证的修复。

## 许可证

[MIT](LICENSE) © 2026 dajiaohuang。
