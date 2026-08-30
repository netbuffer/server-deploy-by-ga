#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
制品交付自动化脚本 (deliver.py)
职责: 
  1. 解析业务仓库中固定的 deploy/artifacts.manifest 声明文件 (若无则回退兜底模式)
  2. 若业务仓库提供 deploy/deploy.sh 部署回调脚本，自动同步传输至服务器
  3. 传送制品前安全清空服务器目标暂存目录
  4. 传输匹配的制品文件到服务器，生成 Markdown 格式的制品清单供钉钉通知使用
"""

import os
import sys
import subprocess
from pathlib import Path

def run_cmd(cmd, check=True):
    """辅助函数: 执行 Shell/SSH 命令"""
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if check and result.returncode != 0:
        print(f"❌ 命令执行失败: {cmd}\n错误输出:\n{result.stderr}")
        sys.exit(result.returncode)
    return result.stdout.strip()

def get_file_size(filepath):
    """获取文件人类可读的大小 (如 12.5M, 450K)"""
    size_bytes = os.path.getsize(filepath)
    for unit in ['B', 'K', 'M', 'G']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}T"

def load_manifest_rules(src_dir):
    """从克隆的业务仓库中读取固定的 deploy/artifacts.manifest 声明规则"""
    manifest_path = src_dir / "deploy" / "artifacts.manifest"
    
    if manifest_path.exists() and manifest_path.is_file():
        print(f"📄 找到业务仓库声明规范文件: deploy/artifacts.manifest")
        rules = []
        with open(manifest_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    rules.append(line)
        return rules
    return None

def should_keep_jar(jar_path, src_dir, manifest_rules, target_services=None):
    """依据 Manifest 规则及 target_services 选择性过滤 JAR"""
    filename = jar_path.name

    # 基础排除
    if filename.endswith(".original") or "wrapper" in filename:
        return False

    # 提取模块名 (例如 workspace_src/gateway/target/gateway.jar -> gateway)
    rel_parts = jar_path.relative_to(src_dir).parts
    mod_dir = rel_parts[0] if len(rel_parts) > 2 else ""
    service_name = mod_dir if mod_dir else filename.replace(".jar", "")

    # 如果用户指定了具体服务列表 (不为 ['all'])
    if target_services and "all" not in target_services:
        matched_service = False
        for target in target_services:
            target = target.strip()
            if target and (target == service_name or target in filename or target == mod_dir):
                matched_service = True
                break
        if not matched_service:
            return False

    # 若无 Manifest 规则，兜底全部保留
    if manifest_rules is None:
        return True

    # 比对 Manifest 规则 (匹配模块名或 jar 文件名)
    for rule in manifest_rules:
        if rule == mod_dir or rule == filename or rule in filename:
            return True
        if "*" in rule:
            import fnmatch
            if fnmatch.fnmatch(mod_dir, rule) or fnmatch.fnmatch(filename, rule):
                return True
    return False

def main():
    server_host = os.getenv("SERVER_HOST")
    server_user = os.getenv("SERVER_USER")
    artifact_dir = os.getenv("TARGET_ARTIFACT_DIR", "/opt/artifacts")
    deploy_service_input = os.getenv("TARGET_DEPLOY_SERVICE", "all").strip()
    target_services = [s.strip() for s in deploy_service_input.split(",") if s.strip()]

    src_dir = Path("workspace_src")

    if not server_host or not server_user:
        print("❌ 错误: SERVER_HOST 或 SERVER_USER 环境变量未配置！")
        sys.exit(1)

    if not src_dir.exists():
        print("❌ 错误: workspace_src 目录不存在！")
        sys.exit(1)

    print(f"🎯 选定的部署服务范围: {deploy_service_input} (解析列表: {target_services})")

    # 1. 解析业务仓库中的声明规范
    manifest_rules = load_manifest_rules(src_dir)
    if manifest_rules is not None:
        print(f"🎯 生效 Manifest 匹配规则 ({len(manifest_rules)} 条): {manifest_rules}")
    else:
        print("ℹ️ 业务仓库未提供 deploy/artifacts.manifest 规范，采用全量制品兜底模式。")

    # 2. 检索并过滤目标 JAR 文件
    all_jars = list(src_dir.glob("**/target/*.jar"))
    target_jars = [j for j in all_jars if should_keep_jar(j, src_dir, manifest_rules, target_services)]

    print(f"📦 共检索到 {len(all_jars)} 个 JAR 包，经规则筛选后保留 {len(target_jars)} 个交付制品:")
    for j in target_jars:
        print(f"   - {j}")

    if not target_jars:
        print("⚠️ 警告: 未找到匹配交付规则的 target/*.jar 制品包！")

    # 3. 传送制品前：安全清空服务器暂存目录
    print(f"\n🧹 正在清空服务器目标暂存目录: {artifact_dir} ...")
    run_cmd(f'ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=5 -n {server_user}@{server_host} "mkdir -p {artifact_dir} && rm -rf {artifact_dir}/*"')

    # 4. 同步交付业务仓库自带的 deploy/deploy.sh 脚本 (如果有)
    repo_deploy_script = src_dir / "deploy" / "deploy.sh"
    if repo_deploy_script.exists() and repo_deploy_script.is_file():
        print(f"📜 发现业务仓库自带部署脚本: deploy/deploy.sh，同步分发至服务器...")
        run_cmd(f'scp -o ServerAliveInterval=30 -o ServerAliveCountMax=5 "{repo_deploy_script}" "{server_user}@{server_host}:{artifact_dir}/deploy.sh"')

    # 5. 传输制品并生成 Markdown 列表
    artifact_list_lines = []
    for jar_path in target_jars:
        filename = jar_path.name
        filesize = get_file_size(jar_path)
        
        rel_parts = jar_path.relative_to(src_dir).parts
        mod_dir = rel_parts[0] if len(rel_parts) > 2 else ""

        if mod_dir and mod_dir != "target":
            target_path = f"{artifact_dir}/{mod_dir}/{filename}"
            run_cmd(f'ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=5 -n {server_user}@{server_host} "mkdir -p {artifact_dir}/{mod_dir}"')
            print(f"🚀 [模块 {mod_dir}] 正在传输 {filename} ({filesize}) -> {target_path} ...")
            run_cmd(f'scp -o ServerAliveInterval=30 -o ServerAliveCountMax=5 "{jar_path}" "{server_user}@{server_host}:{target_path}"')
            artifact_list_lines.append(f"- [{mod_dir}] {filename} ({filesize})")
        else:
            target_path = f"{artifact_dir}/{filename}"
            print(f"🚀 [根模块] 正在传输 {filename} ({filesize}) -> {target_path} ...")
            run_cmd(f'scp -o ServerAliveInterval=30 -o ServerAliveCountMax=5 "{jar_path}" "{server_user}@{server_host}:{target_path}"')
            artifact_list_lines.append(f"- {filename} ({filesize})")

    # 6. 输出制品列表为 GITHUB_ENV 变量供钉钉通知使用
    artifact_list_str = "\n".join(artifact_list_lines) if artifact_list_lines else "- 无"
    github_env = os.getenv("GITHUB_ENV")
    if github_env:
        with open(github_env, "a", encoding="utf-8") as f:
            f.write("ARTIFACT_LIST<<EOF\n")
            f.write(artifact_list_str + "\n")
            f.write("EOF\n")

    print("\n=== 服务器端制品接收验证 ===")
    res = run_cmd(f'ssh -o ServerAliveInterval=30 -o ServerAliveCountMax=5 -n {server_user}@{server_host} "ls -la {artifact_dir}"')
    print(res)

if __name__ == "__main__":
    main()
