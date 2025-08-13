#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Git钩子设置脚本
自动设置Git钩子，实现版本管理自动化

使用方法:
    python scripts/setup_git_hooks.py
"""

import os
import stat
import subprocess
from pathlib import Path


class GitHooksSetup:
    """Git钩子设置器"""
    
    def __init__(self):
        """初始化Git钩子设置器"""
        self.project_root = Path(".")
        self.git_hooks_dir = self.project_root / ".git" / "hooks"
        
        if not self.git_hooks_dir.exists():
            raise Exception("Git仓库未初始化或.git/hooks目录不存在")
    
    def setup_all_hooks(self):
        """设置所有Git钩子"""
        print("🔧 开始设置Git钩子...")
        
        # 设置各种钩子
        self.setup_pre_commit_hook()
        self.setup_commit_msg_hook()
        self.setup_pre_push_hook()
        
        print("✅ Git钩子设置完成！")
    
    def setup_pre_commit_hook(self):
        """设置pre-commit钩子"""
        hook_content = '''#!/bin/sh
# Pre-commit hook for RedNoteAnalyzer
# 在提交前进行代码检查

echo "🔍 运行pre-commit检查..."

# 检查Python语法
echo "📝 检查Python语法..."
python -m py_compile $(git diff --cached --name-only --diff-filter=ACM | grep "\.py$") 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Python语法检查失败"
    exit 1
fi

# 检查代码风格（如果安装了flake8）
if command -v flake8 >/dev/null 2>&1; then
    echo "🎨 检查代码风格..."
    flake8 $(git diff --cached --name-only --diff-filter=ACM | grep "\.py$") 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "⚠️  代码风格检查发现问题，但不阻止提交"
    fi
fi

# 检查大文件
echo "📦 检查大文件..."
for file in $(git diff --cached --name-only --diff-filter=ACM); do
    if [ -f "$file" ]; then
        size=$(wc -c < "$file")
        if [ $size -gt 10485760 ]; then  # 10MB
            echo "❌ 文件 $file 过大 ($(($size / 1048576))MB)，请使用Git LFS"
            exit 1
        fi
    fi
done

echo "✅ Pre-commit检查通过"
exit 0
'''
        
        self._write_hook("pre-commit", hook_content)
        print("✅ Pre-commit钩子已设置")
    
    def setup_commit_msg_hook(self):
        """设置commit-msg钩子"""
        hook_content = '''#!/bin/sh
# Commit message hook for RedNoteAnalyzer
# 检查提交信息格式

commit_regex='^(feat|fix|docs|style|refactor|test|chore|breaking)(\(.+\))?: .{1,50}'

if ! grep -qE "$commit_regex" "$1"; then
    echo "❌ 提交信息格式不正确！"
    echo "📝 正确格式: <type>(<scope>): <description>"
    echo "📋 类型说明:"
    echo "   feat:     新功能"
    echo "   fix:      修复bug"
    echo "   docs:     文档更新"
    echo "   style:    代码格式调整"
    echo "   refactor: 代码重构"
    echo "   test:     测试相关"
    echo "   chore:    构建/工具相关"
    echo "   breaking: 破坏性变更"
    echo ""
    echo "📝 示例:"
    echo "   feat: 添加小红书数据爬取功能"
    echo "   fix(auth): 修复登录验证问题"
    echo "   docs: 更新API文档"
    exit 1
fi

echo "✅ 提交信息格式正确"
exit 0
'''
        
        self._write_hook("commit-msg", hook_content)
        print("✅ Commit-msg钩子已设置")
    
    def setup_pre_push_hook(self):
        """设置pre-push钩子"""
        hook_content = '''#!/bin/sh
# Pre-push hook for RedNoteAnalyzer
# 在推送前进行检查

echo "🚀 运行pre-push检查..."

# 检查是否有未提交的更改
if ! git diff-index --quiet HEAD --; then
    echo "❌ 存在未提交的更改，请先提交"
    exit 1
fi

# 运行测试（如果存在）
if [ -f "test/test_*.py" ] || [ -d "tests" ]; then
    echo "🧪 运行测试..."
    python -m pytest test/ 2>/dev/null || python -m unittest discover tests/ 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "⚠️  测试失败，但不阻止推送"
    else
        echo "✅ 测试通过"
    fi
fi

# 检查版本一致性
echo "🔍 检查版本一致性..."
python -c "
import json
import re
from pathlib import Path

# 检查version.json和pyproject.toml版本是否一致
version_file = Path('version.json')
pyproject_file = Path('pyproject.toml')

if version_file.exists() and pyproject_file.exists():
    with open(version_file) as f:
        version_config = json.load(f)
    
    with open(pyproject_file) as f:
        pyproject_content = f.read()
    
    version_json = version_config.get('version')
    version_match = re.search(r'version\s*=\s*\"([^\"]+)\"', pyproject_content)
    version_pyproject = version_match.group(1) if version_match else None
    
    if version_json != version_pyproject:
        print(f'❌ 版本不一致: version.json({version_json}) vs pyproject.toml({version_pyproject})')
        exit(1)
    else:
        print(f'✅ 版本一致: {version_json}')
" 2>/dev/null

if [ $? -ne 0 ]; then
    echo "⚠️  版本检查失败，但不阻止推送"
fi

echo "✅ Pre-push检查完成"
exit 0
'''
        
        self._write_hook("pre-push", hook_content)
        print("✅ Pre-push钩子已设置")
    
    def _write_hook(self, hook_name: str, content: str):
        """写入钩子文件"""
        hook_path = self.git_hooks_dir / hook_name
        
        # 写入钩子内容
        with open(hook_path, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
        
        # 设置可执行权限
        current_permissions = hook_path.stat().st_mode
        hook_path.chmod(current_permissions | stat.S_IEXEC)
    
    def remove_hooks(self):
        """移除所有钩子"""
        hooks = ["pre-commit", "commit-msg", "pre-push"]
        
        for hook_name in hooks:
            hook_path = self.git_hooks_dir / hook_name
            if hook_path.exists():
                hook_path.unlink()
                print(f"🗑️  已移除 {hook_name} 钩子")
        
        print("✅ 所有钩子已移除")
    
    def check_hooks_status(self):
        """检查钩子状态"""
        hooks = ["pre-commit", "commit-msg", "pre-push"]
        
        print("📋 Git钩子状态:")
        for hook_name in hooks:
            hook_path = self.git_hooks_dir / hook_name
            if hook_path.exists():
                is_executable = os.access(hook_path, os.X_OK)
                status = "✅ 已安装" + (" (可执行)" if is_executable else " (不可执行)")
            else:
                status = "❌ 未安装"
            
            print(f"   {hook_name}: {status}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Git钩子设置工具")
    parser.add_argument("--install", action="store_true", help="安装所有钩子")
    parser.add_argument("--remove", action="store_true", help="移除所有钩子")
    parser.add_argument("--status", action="store_true", help="检查钩子状态")
    
    args = parser.parse_args()
    
    try:
        setup = GitHooksSetup()
        
        if args.install:
            setup.setup_all_hooks()
        elif args.remove:
            setup.remove_hooks()
        elif args.status:
            setup.check_hooks_status()
        else:
            # 默认安装钩子
            setup.setup_all_hooks()
            
    except Exception as e:
        print(f"❌ 错误: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())