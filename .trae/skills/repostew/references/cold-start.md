# Cold Start Initialization

When RepoStew is first invoked for a user (no existing state in `~/.repostew` or fresh workspace):

## 1. Check authentication

```bash
gh auth status
git --version
python --version
```

If `gh` is unavailable, install it first:
- macOS: download from https://github.com/cli/cli/releases
- Linux: use package manager or download release tarball
- Authenticate with `gh auth login`

## 2. Offer private state backup repository

RepoStew maintains mutable state (contribution tracker, PR tracker, notification inbox, checkpoints). Offer to create a private GitHub repository for durable backup:

**Ask the user:**
> RepoStew需要维护持久状态（贡献追踪、PR追踪、通知收件箱等）。是否要创建一个私有GitHub仓库来备份这些状态？
> - 这样可以跨设备同步，在新环境中恢复追踪历史
> - 状态包括：你追踪的仓库、已处理的PR/Issue、通知记录等
> - 仅你可见，不会暴露任何token或凭证

**If user agrees:**
1. Create a private repository:
   ```bash
   gh repo create repostew-state --private --clone=false
   ```
2. Clone it locally:
   ```bash
   gh repo clone <your-handle>/repostew-state ~/.repostew_backup
   ```
3. Initialize state structure:
   ```bash
   mkdir -p ~/.repostew_backup/.repostew
   mkdir -p ~/.repostew_backup/.repostew-comments
   cp ~/.repostew/*.json ~/.repostew_backup/.repostew/ 2>/dev/null || true
   ```
4. Commit and push:
   ```bash
   cd ~/.repostew_backup
   git add .repostew/ .repostew-comments/
   git commit -m "Initial RepoStew state backup"
   git push origin main
   ```

**If user declines:** Continue without durable backup; state remains local only.

## 3. Set up FOLLOWED_REPOSITORIES.md

If the workspace contains a `FOLLOWED_REPOSITORIES.md`, keep it updated. If not, create a template:

```markdown
# Followed Repositories

## active
- owner/repo

## paused
- owner/paused-repo
```

## Periodic State Sync

If a private backup repository exists (`~/.repostew_backup`), sync state periodically or after significant changes:

```bash
# Sync state files to backup
cp ~/.repostew/contributions.json ~/.repostew_backup/.repostew/
cp ~/.repostew/notification_inbox.json ~/.repostew_backup/.repostew/
cp ~/.repostew/pr_tracker.json ~/.repostew_backup/.repostew/ 2>/dev/null || true

# Commit and push
cd ~/.repostew_backup
git add .repostew/*.json
git commit -m "Sync: $(date '+%Y-%m-%d %H:%M:%S')"
git push origin main
```
