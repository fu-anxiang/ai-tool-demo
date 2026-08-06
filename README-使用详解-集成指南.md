# AI 工具开发流水线 · 使用详解与集成指南

> 环境：WSL2 Ubuntu（dev 用户）+ Docker CE + Gitea(3000) + Registry(5000) + act_runner + ai-sandbox 沙箱
> 项目：/opt/ci/repos/ai-tool-demo（参考项目，可复制模板）

---

## 一、整体工作流程

```
┌─────────────┐   Remote-WSL    ┌──────────────────┐
│   VS Code   │ ──────────────> │  WSL (dev 用户)   │
└─────────────┘                 └────────┬─────────┘
                                         │ git push（触发流水线）
                                         ▼
                              ┌─────────────────────┐
                              │  Gitea :3000         │
                              └──────────┬──────────┘
                                         │ Gitea Actions
                                         ▼
        ┌────────────────────────────────────────────────────┐
        │ ① sandbox-check  危险代码沙箱预检                    │
        │     · danger-scan 静态扫描（递归删根、管道执行、      │
        │       全盘提权、解码执行等恶意模式）                  │
        │     · pytest（tests/test_malware.py 正则检测）       │
        │     · 实弹测试（一次性沙箱容器内执行恶意行为）         │
        │    ❌ 发现危险代码 → 流水线红，后续阶段自动阻断        │
        ├────────────────────────────────────────────────────┤
        │ ② build-push   通过预检的可信阶段                    │
        │     · docker build → 推送到本地 registry :5000       │
        ├────────────────────────────────────────────────────┤
        │ ③ deploy       本地部署                             │
        │     · docker run -p 8080 + 冒烟测试（health/analyze）│
        └────────────────────────────────────────────────────┘
                         │
             代码同步（可选，见第四章）
                         ▼
                 GitHub 仓库（双远程推送）
```

**核心安全设计**：危险代码阶段（①）在无 Docker 权限的非 root 沙箱容器中执行，恶意代码无法触达宿主机；构建/部署阶段（②③）只执行已通过沙箱预检的代码。

---

## 二、日常开发工作流（5 步）

### 1. 进入 WSL 工作目录
```bash
cd /opt/ci/repos/ai-tool-demo
```

### 2. 写代码（VS Code 见第三章）

### 3. 提交并推送（自动触发流水线）
```bash
git add -A
git commit -m "feat: 描述你的改动"
git push
```
> 推送即触发：沙箱预检 → 测试 → 构建镜像 → 推送 registry → 本地部署，全程约 1-2 分钟。

### 4. 查看流水线结果
- 浏览器：http://localhost:3000/gitea_admin/ai-tool-demo/actions
- 或命令行查最近一次运行：
```bash
docker exec gitea sqlite3 /data/gitea/gitea.db \
  "SELECT id,job_id,status FROM action_run_job WHERE run_id=(SELECT max(id) FROM action_run);"
```
status：2=已完成，4=失败/阻断；**以 job 日志为准**：
```bash
docker exec gitea sh -c 'tail -5 /data/gitea/data/actions_log/gitea_admin/ai-tool-demo/*/*.log'
```

### 5. 验证部署
```bash
curl localhost:8080/health
curl -X POST localhost:8080/analyze -H "Content-Type: application/json" -d '{"text":"I love this tool"}'
```

---

## 三、VS Code 集成 Gitea + 沙箱

### 3.1 用 Remote-WSL 打开项目（推荐）
1. VS Code 扩展 `ms-vscode-remote.remote-wsl` 已装 ✓
2. WSL 终端执行：`cd /opt/ci/repos/ai-tool-demo && code .`
3. VS Code 自动以 Remote-WSL 模式打开，左下角显示 `WSL: Ubuntu`
4. 内置 Git 面板（Ctrl+Shift+G）可直接查看 diff、提交、推送

### 3.2 用 SSH 免密访问 Gitea（可选）
SSH key 已生成（dev 用户 ~/.ssh/id_ed25519）并注册到 Gitea。克隆/推送可用：
```bash
# 使用别名 gitea-local（SSH config 已配好 localhost:2222）
git clone ssh://gitea-local/gitea_admin/ai-tool-demo.git
```
VS Code 打开仓库时，Git 面板会显示 gitea 与 github 两个远程源。

### 3.3 安装 Gitea 扩展（可选，浏览 Issue/PR）
```bash
code --install-extension gitea.vscode-gitea
```
配置：Settings 填 Gitea URL `http://localhost:3000` 与 API Token（/opt/ci/.admin-token 里的值）。

### 3.4 在沙箱容器里开发（Dev Containers 可选）
Remote-Containers 已装。打开项目目录选 "Reopen in Container" + `ai-sandbox:latest` 即可在隔离环境内开发（ai-sandbox 非 root，写文件受限，适合只读检查/测试）。

---

## 四、与 GitHub 仓库联动（双远程）

### 4.1 把 SSH key 添加到 GitHub（一次性）
1. 复制公钥：`cat ~/.ssh/id_ed25519.pub`
2. GitHub → Settings → SSH and GPG keys → New SSH key，粘贴保存
3. 验证：`ssh -T git@github.com`（走 443 通道，国内可用；首次提示确认输入 yes）

### 4.2 添加 GitHub 远程
```bash
cd /opt/ci/repos/ai-tool-demo
git remote add github git@github.com:<你的用户名>/<仓库名>.git
```

### 4.3 一键双推（Gitea 流水线 + GitHub 同步）
```bash
cat > /opt/ci/repos/ai-tool-demo/git-sync.sh <<'EOF'
#!/bin/bash
# 用法: bash git-sync.sh "commit message"
set -e
cd "$(dirname "$0")"
git add -A
git commit -m "${1:-sync}" || echo "(nothing to commit)"
git push gitea main        # 触发本地 CI/CD 流水线
git push github main       # 同步到 GitHub
echo "[OK] pushed to gitea + github"
EOF
chmod +x /opt/ci/repos/ai-tool-demo/git-sync.sh
cd /opt/ci/repos/ai-tool-demo && git remote rename origin gitea 2>/dev/null || true
```
之后每次：`bash git-sync.sh "feat: xxx"` —— 一条命令同时完成部署和上传 GitHub。

### 4.4 在 GitHub 上跑同样的流水线（✅ 已配置启用）
- ✅ 已配置：`.github/workflows/ci.yaml`（ci-publish 工作流，push main/tag/PR 触发）
- 差异点（GitHub 版实现）：
  1. GitHub Actions runner 有完整网络：checkout 用 `actions/checkout@v4`，无需网关 hack
  2. 本地 registry 改为 GitHub Container Registry（ghcr.io）或 Docker Hub，需配置 secrets
  3. 部署步骤改为"构建产物上传"或"触发远端部署"（GitHub runner 不共享你的本机 Docker）
- 即：**本地流水线用于"沙箱验证 + 本地部署"，GitHub 流水线用于"对外发布"**，二者互补

---

## 五、流水线各阶段详解

| 阶段 | 容器环境 | 做什么 | 失败后果 |
|---|---|---|---|
| sandbox-check | ai-sandbox（非 root，无 docker.sock） | danger-scan 静态扫描 → pytest（6 用例，含恶意模式检测）→ 实弹测试（一次性容器内执行恶意行为） | 流水线红，后续阻断 |
| build-push | ai-sandbox（root + docker.sock） | docker build（python:3.12-slim + 清华 pip 源）→ docker push 127.0.0.1:5000（latest + commit sha 双 tag） | 不部署 |
| deploy | ai-sandbox（root + docker.sock） | 删旧容器 → docker run -p 8080 → docker exec 冒烟测试（health + analyze） | 部署失败 |

危险模式清单（danger-scan.sh + test_malware.py）：递归删除根目录、进程炸弹、解码后管道执行、curl/wget 管道执行、全盘权限提权、块设备直写、磁盘格式化。命中即 [BLOCKED]。所有模式以正则/拼接形式存在，避免误报与自匹配。

---

## 六、常用管理命令

```bash
# 服务状态
docker compose -f /opt/ci/docker-compose.yml ps

# 重启 runner（流水线异常时）
docker compose -f /opt/ci/docker-compose.yml restart runner

# 查看 registry 里的镜像
curl localhost:5000/v2/_catalog
curl localhost:5000/v2/ai-tool-demo/tags/list

# 手动构建沙箱镜像（改了 Dockerfile 后）
cd /opt/ai-agent-sandbox && sudo bash build-sandbox.sh
docker push 127.0.0.1:5000/ai-sandbox:latest   # 同步给 CI 用

# 手动跑危险代码测试
bash /opt/ai-agent-sandbox/test-malware.sh
```

---

## 七、常见问题

| 问题 | 解决 |
|---|---|
| 流水线 job 显示 running 但日志已结束 | act_runner 状态上报偶发延迟，看日志确认真实结果 |
| git push 提示 dubious ownership | 仓库属主不对：`sudo chown -R dev:dev /opt/ci/repos` |
| 沙箱预检红 | 看日志哪个模式命中；误报则把检测器模式拆分/豁免 |
| 需要更多语言运行时 | 改 /opt/ai-agent-sandbox/Dockerfile 重建 + 推送 registry |
| GitHub push 失败 | 确认 SSH key 已加、`ssh -T git@github.com` 可通（443 通道） |