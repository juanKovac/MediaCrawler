#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发布管理工具
自动化项目发布流程，包括版本更新、标签创建、CHANGELOG更新等

使用方法:
    python scripts/release.py --type [major|minor|patch]
    python scripts/release.py --auto  # 根据提交信息自动判断
    python scripts/release.py --prepare  # 准备发布（不创建标签）
"""

import json
import re
import subprocess
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from version_manager import VersionManager


class ReleaseManager:
    """发布管理器"""
    
    def __init__(self):
        """初始化发布管理器"""
        self.version_manager = VersionManager()
        self.changelog_path = Path("CHANGELOG.md")
        self.project_root = Path(".")
    
    def prepare_release(self, bump_type: str, description: str = "") -> str:
        """准备发布
        
        Args:
            bump_type: 版本更新类型
            description: 发布描述
            
        Returns:
            新版本号
        """
        print("🚀 开始准备发布...")
        
        # 检查工作目录是否干净
        if not self._is_working_directory_clean():
            raise Exception("工作目录不干净，请先提交或暂存所有更改")
        
        # 更新版本号
        print(f"📝 更新版本号 ({bump_type})...")
        new_version = self.version_manager.bump_version(bump_type, description)
        print(f"✅ 版本已更新为: {new_version}")
        
        # 更新 CHANGELOG
        print("📋 更新 CHANGELOG...")
        self._update_changelog(new_version)
        print("✅ CHANGELOG 已更新")
        
        # 提交版本更新
        print("💾 提交版本更新...")
        self._commit_version_update(new_version)
        print("✅ 版本更新已提交")
        
        return new_version
    
    def create_release(self, bump_type: str, description: str = "", push: bool = True) -> str:
        """创建发布
        
        Args:
            bump_type: 版本更新类型
            description: 发布描述
            push: 是否推送到远程仓库
            
        Returns:
            新版本号
        """
        # 准备发布
        new_version = self.prepare_release(bump_type, description)
        
        # 创建 Git 标签
        print("🏷️  创建 Git 标签...")
        self.version_manager.create_git_tag(new_version)
        print(f"✅ 已创建标签: v{new_version}")
        
        # 推送到远程仓库
        if push:
            print("📤 推送到远程仓库...")
            self._push_to_remote(new_version)
            print("✅ 已推送到远程仓库")
        
        print(f"🎉 发布 v{new_version} 完成！")
        return new_version
    
    def auto_release(self, push: bool = True) -> str:
        """自动发布
        
        Args:
            push: 是否推送到远程仓库
            
        Returns:
            新版本号
        """
        print("🤖 开始自动发布...")
        
        # 获取最新提交信息
        commit_msg = self._get_latest_commit_message()
        print(f"📝 最新提交: {commit_msg}")
        
        # 自动判断版本类型
        bump_type = self.version_manager._determine_bump_type(commit_msg)
        print(f"🔍 自动判断版本类型: {bump_type}")
        
        return self.create_release(bump_type, commit_msg, push)
    
    def _is_working_directory_clean(self) -> bool:
        """检查工作目录是否干净"""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                check=True
            )
            return len(result.stdout.strip()) == 0
        except subprocess.CalledProcessError:
            return False
    
    def _get_latest_commit_message(self) -> str:
        """获取最新提交信息"""
        try:
            result = subprocess.run(
                ["git", "log", "-1", "--pretty=format:%s"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise Exception(f"无法获取提交信息: {e}")
    
    def _update_changelog(self, version: str):
        """更新 CHANGELOG.md"""
        if not self.changelog_path.exists():
            print("警告: CHANGELOG.md 不存在，跳过更新")
            return
        
        try:
            with open(self.changelog_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 获取版本历史
            config = self.version_manager.config
            version_history = config.get("version_history", [])
            
            # 找到当前版本的记录
            current_version_entry = None
            for entry in reversed(version_history):
                if entry["version"] == version:
                    current_version_entry = entry
                    break
            
            if not current_version_entry:
                print("警告: 未找到当前版本的历史记录")
                return
            
            # 生成新的版本条目
            date = current_version_entry.get("date", datetime.now().strftime("%Y-%m-%d"))
            changes = current_version_entry.get("changes", [])
            
            version_entry = f"\n## [{version}] - {date}\n\n"
            
            if changes:
                version_entry += "### 变更\n"
                for change in changes:
                    version_entry += f"- {change}\n"
                version_entry += "\n"
            
            # 在 [未发布] 部分后插入新版本
            unreleased_pattern = r'(## \[未发布\].*?)(\n## \[)'
            if re.search(unreleased_pattern, content, re.DOTALL):
                # 清空未发布部分
                content = re.sub(
                    r'(## \[未发布\]\s*)(.*?)(\n## \[)',
                    f'\\1\n### 新增\n- 待添加\n\n### 变更\n- 待添加\n\n### 修复\n- 待添加\n{version_entry}\\3',
                    content,
                    flags=re.DOTALL
                )
            else:
                # 如果没有未发布部分，在开头添加
                header_end = content.find('\n## ')
                if header_end != -1:
                    content = content[:header_end] + version_entry + content[header_end:]
            
            with open(self.changelog_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
        except Exception as e:
            print(f"更新 CHANGELOG 失败: {e}")
    
    def _commit_version_update(self, version: str):
        """提交版本更新"""
        try:
            # 添加所有更改的文件
            subprocess.run(["git", "add", "."], check=True)
            
            # 提交更改
            commit_message = f"chore: release v{version}"
            subprocess.run(
                ["git", "commit", "-m", commit_message],
                check=True
            )
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"提交版本更新失败: {e}")
    
    def _push_to_remote(self, version: str):
        """推送到远程仓库"""
        try:
            # 推送提交
            subprocess.run(["git", "push"], check=True)
            
            # 推送标签
            subprocess.run(["git", "push", "--tags"], check=True)
            
        except subprocess.CalledProcessError as e:
            raise Exception(f"推送到远程仓库失败: {e}")
    
    def show_release_info(self):
        """显示发布信息"""
        current_version = self.version_manager._get_current_version()
        print(f"📦 当前版本: {current_version}")
        
        # 显示未提交的更改
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True
            )
            
            if result.stdout.strip():
                print("⚠️  未提交的更改:")
                for line in result.stdout.strip().split('\n'):
                    print(f"   {line}")
            else:
                print("✅ 工作目录干净")
                
        except subprocess.CalledProcessError:
            print("❌ 无法检查Git状态")
        
        # 显示最近的提交
        try:
            result = subprocess.run(
                ["git", "log", "--oneline", "-5"],
                capture_output=True,
                text=True,
                encoding='utf-8',
                check=True
            )
            
            print("\n📝 最近的提交:")
            for line in result.stdout.strip().split('\n'):
                if line:
                    print(f"   {line}")
                    
        except subprocess.CalledProcessError:
            print("❌ 无法获取提交历史")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="发布管理工具")
    parser.add_argument("--type", choices=["major", "minor", "patch"], help="发布类型")
    parser.add_argument("--auto", action="store_true", help="自动发布")
    parser.add_argument("--prepare", action="store_true", help="仅准备发布（不创建标签）")
    parser.add_argument("--info", action="store_true", help="显示发布信息")
    parser.add_argument("--no-push", action="store_true", help="不推送到远程仓库")
    parser.add_argument("--description", "-d", help="发布描述")
    
    args = parser.parse_args()
    
    try:
        rm = ReleaseManager()
        
        if args.info:
            rm.show_release_info()
        elif args.prepare and args.type:
            new_version = rm.prepare_release(args.type, args.description or "")
            print(f"\n🎯 发布已准备完成: v{new_version}")
            print("💡 运行以下命令创建标签并推送:")
            print(f"   python scripts/release.py --type {args.type} --description '{args.description or ''}'")
        elif args.type:
            push = not args.no_push
            new_version = rm.create_release(args.type, args.description or "", push)
            print(f"\n🎉 发布完成: v{new_version}")
        elif args.auto:
            push = not args.no_push
            new_version = rm.auto_release(push)
            print(f"\n🎉 自动发布完成: v{new_version}")
        else:
            parser.print_help()
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())