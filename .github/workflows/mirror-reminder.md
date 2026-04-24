# GitHub mirror reminder

This repo currently uses Gitea as the source-of-truth remote.

Before GitHub-based releases work, add a GitHub repo and either:
- add it as a second remote and push to both, or
- configure Gitea-side mirroring to GitHub

Suggested remote:

```bash
git remote add github https://github.com/NewCapricaOpenClaw/wikijs-client.git
```

Suggested first push:

```bash
git push github main --tags
```

If PyPI publishing is enabled from GitHub Actions, prefer PyPI Trusted Publishing for the GitHub repo rather than storing a long-lived API token.
