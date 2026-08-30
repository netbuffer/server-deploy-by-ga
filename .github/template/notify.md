### 🚀 服务构建与交付通知

- **目标仓库**: `${USING_REPO}`
- **目标分支**: `${USING_REF}`
- **触发用户**: `${GITHUB_ACTOR}`
- **构建状态**: `${JOB_STATUS}`
- **制品存放目录**: `${TARGET_ARTIFACT_DIR}`
- **回调 Hook 脚本**: `${TARGET_HOOK_SCRIPT}`
- **Run ID**: [${GITHUB_RUN_ID}](https://github.com/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID})

---
#### 📦 交付制品文件列表
```text
${ARTIFACT_LIST}
```
