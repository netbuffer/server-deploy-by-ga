# AGENTS.md - 编程智能体 (AI Coding Agent) 行为约束与规范指南

本文件是针对所有参与本仓库代码修改、维护与重构的 AI 编程智能体（Agents）的硬性行为准则。
在对本仓库进行任何代码或配置文件修改之前，**必须严格遵守以下规范**。

---

## 1. 核心铁律 (Core Constraints)

### 🚨 1.1 绝对零硬编码 (Strictly No Hardcoding)
- **严禁写死隐私与特定信息**：禁止在 `.yml`、`.md` 或任何脚本文件中出现特定的公网/内网 IP 地址、域名（如 `*.xxx.com` 等）、物理路径（如 `/home/xxx`）、特定项目名或敏感密钥。
- **全量配置与环境变量驱动**：所有主机地址、域名、用户凭据、项目路径、文件相对位置**必须**通过 GitHub Secrets、`inputs` 参数或 `env` 环境变量进行动态注入与回退控制。

### 🛡️ 1.2 纯粹职责边界与通用性 (Separation of Responsibilities)
- **云端仅负责构建与交付**：GitHub Actions 仅负责编译打包、分发制品至 `${SERVER_ARTIFACT_DIR}` 并触发 `${SERVER_HOOK_SCRIPT}`。
- **运维逻辑归属服务器**：严禁在 GitHub Actions 工作流中硬编码特定的服务器启动逻辑（如强制指定某些 docker 命令或进程重启逻辑）。
- **平台无偏见**：工作流必须兼容任意标准的 Git 托管平台（如 GitLab、GitHub、Gitea、Gitee、Codeup 等），不得假定单一云厂商。

---

## 2. CI/CD 工作流维护规范 (.github/workflows/)

1. **语法校验**：
   - 在 `job.steps.if` 条件表达式中**严禁直接引用 `secrets.*`** 命名空间，必须映射至 `env` 后通过 `env.XXX` 进行判断。
2. **依赖更新**：
   - 修改或添加 GitHub Actions 官方插件时，必须查询并使用官方验证的**最新 release 标签**（如 `actions/setup-java@v6.0.0`），禁止盲目凭空预测或使用已废弃的旧版本。
3. **零误杀告警**：
   - 对于可选步骤（如钉钉/飞书通知），当对应的 Secret/Token 为空时，必须使用条件判断优雅跳过，严禁报错中断整体 Job。

---

## 3. Git 提交与变更控制 (Commit & Push Rules)

- **提交信息**：使用 Concise Conventional Commits 规范（如 `feat: ...`, `fix: ...`, `refactor: ...`, `docs: ...`）。
- **历史干净**：重构大版本时，优先推荐 Orphan 清理历史保持单提交干净状态。
- **文件清理**：不得在仓库根目录产生临时测试文件、编译中间产物或未经脱敏的日志文本。
