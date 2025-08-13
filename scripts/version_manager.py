#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
版本管理工具
自动根据Git提交信息更新版本号，遵循语义化版本控制规范

使用方法:
    python scripts/version_manager.py --bump [major|minor|patch]
    python scripts/version_manager.py --auto  # 根据最新提交自动判断版本类型
    python scripts/version_manager.py --current  # 显示当前版本
"""

import json
import re
import subprocess
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple


class VersionManager:
    """版本管理器"""
    
    def __init__(self, config_path: str = "version.json"):
        """初始化版本管理器
        
        Args:
            config_path: 版本配置文件路径
        """
        self.config_path = Path(config_path)
        self.pyproject_path = Path("pyproject.toml")
        self.config = self._load_config()
    
    def _load_config(self) -> Dict:
        """加载版本配置文件"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"版本配置文件不存在: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _save_config(self):
        """保存版本配置文件"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)
    
    def _get_current_version(self) -> str:
        """获取当前版本号"""
        return self.config.get("version", "0.1.0")
    
    def _parse_version(self, version: str) -> Tuple[int, int, int]:
        """解析版本号为三元组
        
        Args:
            version: 版本号字符串，如 "1.2.3"
            
        Returns:
            (major, minor, patch) 三元组
        """
        parts = version.split('.')
        if len(parts) != 3:
            raise ValueError(f"无效的版本号格式: {version}")
        
        return tuple(map(int, parts))
    
    def _format_version(self, major: int, minor: int, patch: int) -> str:
        """格式化版本号"""
        return f"{major}.{minor}.{patch}"
    
    def bump_version(self, bump_type: str, description: str = "") -> str:
        """更新版本号
        
        Args:
            bump_type: 版本更新类型 (major, minor, patch)
            description: 版本描述
            
        Returns:
            新的版本号
        """
        current_version = self._get_current_version()
        major, minor, patch = self._parse_version(current_version)
        
        if bump_type == "major":
            major += 1
            minor = 0
            patch = 0
        elif bump_type == "minor":
            minor += 1
            patch = 0
        elif bump_type == "patch":
            patch += 1
        else:
            raise ValueError(f"无效的版本更新类型: {bump_type}")
        
        new_version = self._format_version(major, minor, patch)
        
        # 更新配置
        self.config["version"] = new_version
        
        # 添加到版本历史
        version_entry = {
            "version": new_version,
            "date": datetime.now().strftime("%Y-%m-%d"),
            "type": bump_type,
            "description": description or f"{bump_type.capitalize()} version update",
            "changes": self._get_recent_commits()
        }
        
        if "version_history" not in self.config:
            self.config["version_history"] = []
        
        self.config["version_history"].append(version_entry)
        
        # 保存配置
        self._save_config()
        
        # 更新 pyproject.toml
        self._update_pyproject_version(new_version)
        
        return new_version
    
    def _get_recent_commits(self, count: int = 10) -> List[str]:
        """获取最近的提交信息"""
        try:
            result = subprocess.run(
                ["git", "log", f"--oneline", f"-{count}"],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode == 0:
                commits = result.stdout.strip().split('\n')
                return [commit.split(' ', 1)[1] if ' ' in commit else commit for commit in commits if commit]
            
        except Exception as e:
            print(f"获取提交信息失败: {e}")
        
        return []
    
    def _update_pyproject_version(self, new_version: str):
        """更新 pyproject.toml 中的版本号"""
        if not self.pyproject_path.exists():
            print("警告: pyproject.toml 文件不存在")
            return
        
        try:
            with open(self.pyproject_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 使用正则表达式替换版本号
            pattern = r'(version\s*=\s*")[^"]+(")'
            replacement = f'\\g<1>{new_version}\\g<2>'
            new_content = re.sub(pattern, replacement, content)
            
            with open(self.pyproject_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            print(f"已更新 pyproject.toml 中的版本号为: {new_version}")
            
        except Exception as e:
            print(f"更新 pyproject.toml 失败: {e}")
    
    def auto_bump(self) -> str:
        """根据最新提交自动判断版本更新类型"""
        try:
            # 获取最新提交信息
            result = subprocess.run(
                ["git", "log", "-1", "--pretty=format:%s"],
                capture_output=True,
                text=True,
                encoding='utf-8'
            )
            
            if result.returncode != 0:
                raise Exception("无法获取Git提交信息")
            
            commit_msg = result.stdout.strip()
            print(f"最新提交: {commit_msg}")
            
            # 根据提交信息判断版本类型
            bump_type = self._determine_bump_type(commit_msg)
            print(f"自动判断版本更新类型: {bump_type}")
            
            return self.bump_version(bump_type, commit_msg)
            
        except Exception as e:
            print(f"自动版本更新失败: {e}")
            return self._get_current_version()
    
    def _determine_bump_type(self, commit_msg: str) -> str:
        """根据提交信息判断版本更新类型"""
        commit_types = self.config.get("auto_increment", {}).get("commit_types", {})
        
        # 检查是否包含破坏性变更标识
        if "BREAKING CHANGE" in commit_msg or "breaking:" in commit_msg.lower():
            return "major"
        
        # 根据提交类型前缀判断
        for commit_type, bump_type in commit_types.items():
            if commit_msg.lower().startswith(f"{commit_type}:") or commit_msg.lower().startswith(f"{commit_type}("):
                return bump_type
        
        # 默认为 patch
        return "patch"
    
    def create_git_tag(self, version: str = None):
        """创建Git标签"""
        if version is None:
            version = self._get_current_version()
        
        tag_name = f"v{version}"
        
        try:
            # 创建标签
            subprocess.run(
                ["git", "tag", "-a", tag_name, "-m", f"Release {tag_name}"],
                check=True
            )
            print(f"已创建Git标签: {tag_name}")
            
        except subprocess.CalledProcessError as e:
            print(f"创建Git标签失败: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="版本管理工具")
    parser.add_argument("--bump", choices=["major", "minor", "patch"], help="手动指定版本更新类型")
    parser.add_argument("--auto", action="store_true", help="根据最新提交自动更新版本")
    parser.add_argument("--current", action="store_true", help="显示当前版本")
    parser.add_argument("--tag", action="store_true", help="创建Git标签")
    parser.add_argument("--description", "-d", help="版本描述")
    
    args = parser.parse_args()
    
    try:
        vm = VersionManager()
        
        if args.current:
            print(f"当前版本: {vm._get_current_version()}")
        elif args.bump:
            new_version = vm.bump_version(args.bump, args.description or "")
            print(f"版本已更新为: {new_version}")
            if args.tag:
                vm.create_git_tag(new_version)
        elif args.auto:
            new_version = vm.auto_bump()
            print(f"版本已自动更新为: {new_version}")
            if args.tag:
                vm.create_git_tag(new_version)
        elif args.tag:
            vm.create_git_tag()
        else:
            parser.print_help()
            
    except Exception as e:
        print(f"错误: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())