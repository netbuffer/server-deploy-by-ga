# 🚀 server-deploy-by-ga

> **通用、零硬编码、基于声明式约定的多语言 CI/CD 自动化构建与制品交付引擎**

[![GitHub License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-blueviolet.svg)](https://github.com/features/actions)
[![DevOps](https://img.shields.io/badge/DevOps-GitOps-success.svg)](#-核心设计理念)

本工程采用 **“云端免费算力构建 -> 自动化制品交付 -> 远程 Shell Hook 触发”** 的架构设计，彻底解耦 GitHub 编译算力与服务器本地运维启动逻辑。

---

## 💡 核心设计理念

```text
┌────────────────────────────────┐        SSH / SCP        ┌────────────────────────────────┐
│      GitHub Actions 云端       │ ──────────────────────► │       目标云服务器 (ECS)       │
│  (拉取源码 + 编译构建 .jar)    │  1. 清空并交付制品      │  (制品存放至 SERVER_ARTIFACT_DIR)│
└────────────────────────────────┘  2. 同步 deploy.sh      └────────────────────────────────┘
                 │                  3. 触发 Hook 脚本                     │
                 ▼                                                        ▼
   [.github/scripts/deliver.py]                              [bash deploy.sh <ARTIFACT_DIR>]
  根据 artifacts.manifest 过滤制品                             执行重启/容器更新/健康探活检查
```

1. **算力与运维彻底解耦**：GitHub Actions 仅作为纯粹的构建与传输管道，服务器如何重启服务（`docker compose` / `systemctl` / `PM2`）完全由服务器端 Shell 脚本自主决定；
2. **声明式 GitOps 规范**：
   * **制品过滤规范**：业务仓库可通过 `deploy/artifacts.manifest` 自由配置需要分发的模块白名单；
   * **部署脚本规范**：业务仓库可通过 `deploy/.github/deploy.sh` 随代码版本化提交部署逻辑，无需在服务器手工驻留脚本；
3. **多语言与多分支灵活调度**：
   * 针对不同语言栈（Java Maven、Node.js 前端、Go、Python）独立编排 Workflow 管道；
   * 支持通过 `git_ref` 动态选择部署任意 Branch（如 `main`/`master`/`dev`）、Release Tag 或 Commit Hash。

---

## 📁 目录结构

```text
server-deploy-by-ga/
├── .github/
│   ├── scripts/
│   │   ├── deliver.py             # 🐍 核心: 通用制品匹配、清空与 SCP 分发脚本
│   │   └── send-dingtalk.js       # 📢 核心: 模板化钉钉 Markdown 通知脚本 (支持加签)
│   ├── template/
│   │   └── notify.md              # 📝 钉钉通知 Markdown 消息模版
│   └── workflows/
│       ├── deploy-java.yml        # ☕ Java Maven 自动化构建与交付 Pipeline
│       ├── deploy-node.yml        # 🟢 Node.js / 前端构建 Pipeline (占位)
│       ├── deploy-go.yml          # 🔀 Golang 构建 Pipeline (占位)
│       └── deploy-python.yml      # 🐍 Python 构建 Pipeline (占位)
├── docs/                          # 📐 架构设计与 PlantUML 时序/组件设计图
│   ├── architecture.puml          # PlantUML 架构时序图
│   ├── component-architecture.puml# PlantUML 组件架构图
│   └── README.md                  # 架构设计说明
├── AGENTS.md                      # 🤖 AI 编程智能体行为约束
└── README.md                      # 📖 配置指引说明文档
```

---

## ⚙️ 预置密钥配置 (GitHub Secrets)

在 GitHub 仓库 **Settings -> Secrets and variables -> Actions** 中配置以下变量：

| Secret 名称 | 必须 | 说明 | 示例 |
| :--- | :---: | :--- | :--- |
| `SERVER_HOST` | **是** | 目标服务器公网 IP 或域名 | `39.xxx.xxx.xxx` |
| `SERVER_USER` | **是** | SSH 登录用户名 | `root` |
| `SERVER_SSH_KEY` | **是** | 登录服务器的 SSH 私钥 | `-----BEGIN OPENSSH PRIVATE KEY----- ...` |
| `GIT_SSH_KEY` | **是** | 私有 Git 仓库的拉取私钥 | `-----BEGIN OPENSSH PRIVATE KEY----- ...` |
| `GIT_REPO_URL` | **是** | 默认 Git SSH 仓库地址 | `git@your-git-host.com:org/repo.git` |
| `SERVER_ARTIFACT_DIR` | 否 | (可选) 服务器接收制品的物理目录 | `/opt/artifacts` *(默认)* |
| `DINGTALK_WEBHOOK` | 否 | (可选) 钉钉机器人 Webhook 地址 | `https://oapi.dingtalk.com/...` |
| `DINGTALK_SECRET` | 否 | (可选) 钉钉机器人安全加签 Secret | `SEC...` |

---

## 📄 业务仓库约定规范

在你的**业务代码仓库**中，推荐建立以下 `deploy/` 目录结构：

### 1. `deploy/artifacts.manifest` (制品分发白名单)
指定需要交付至服务器的服务模块名称（未配置时默认全量交付）：
```text
gateway
user-server
oauth2-server
wechat-third-platform
intelli-edu-service
```

### 2. `deploy/.github/deploy.sh` (远程回调部署脚本)
随业务代码提交的增量重启与健康检查脚本，脚本接收第一参数 `$1` 为 `${SERVER_ARTIFACT_DIR}` 暂存区路径：
```bash
#!/usr/bin/env bash
ARTIFACT_DIR="${1:-/opt/artifacts}"
# 执行覆盖、docker compose up -d 及健康检查...
```

---

## 🚀 触发交付与使用

1. 进入 GitHub 仓库控制台 $\rightarrow$ 点击 **Actions** 标签页；
2. 选择具体的语言管道（例如 **Build & Deliver (Java Maven)**）；
3. 点击右侧 **Run workflow** 按钮，可自由指定：
   * **git_repo_url**: 动态指定要拉取的 Git 仓库
   * **git_ref**: 动态指定部署分支 / Tag / Commit (默认 `main`)
   * **server_artifact_dir**: 动态指定服务器制品接收目录 (默认 `/opt/artifacts`)

---

## 📄 开源协议

本项目基于 [MIT License](LICENSE) 开源。
