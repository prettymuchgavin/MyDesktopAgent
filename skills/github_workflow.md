---
name: GitHub & Git Operations
description: Interacting with Git repositories, reviewing branches, status, commits, and GitHub navigation.
triggers: git, github, commit, push, pull, repository, branch, pr, repo
---

# GitHub & Git Workflow Skill

When the user asks you to interact with Git or GitHub:

## Recommended Fast Workflow:
1. **Local Git Status Check**: Use `run_command` with `git status` or `git log -n 5 --oneline` to inspect local workspace state.
2. **Online GitHub Navigation**:
   - If asked to navigate or view GitHub, use `open_url` with `https://github.com/...`.
   - Use `web_search` or `fetch_url` to inspect public GitHub APIs or repository READMEs quickly.
3. **Commit & Push Assistance**:
   - Verify modified files before staging.
   - Run standard commands: `git add .` -> `git commit -m "..."` -> `git push`.
4. **Completion**: Verify repository status and confirm result to user.
