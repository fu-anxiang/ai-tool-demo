#!/bin/bash
# 一键双推: Gitea(触发本地流水线) + GitHub(同步)
# 用法: bash git-sync.sh "commit message"
set -e
cd "$(dirname "$0")"
git add -A
git commit -m "${1:-sync}" || echo "(nothing to commit)"
git push gitea main 2>&1 | tail -1
git push github main 2>&1 | tail -1 || echo "[WARN] github remote 未配置或推送失败 (见手册第四章)"
echo "[OK] 推送完成"
