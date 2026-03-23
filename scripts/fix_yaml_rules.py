#!/usr/bin/env python3
"""
YAML规则文件修复和优化脚本
- 合并重复的pattern键
- 优化正则表达式结构
- 添加误报过滤
"""

import yaml
import re
import os
from pathlib import Path
from collections import defaultdict
import shutil

# 备份目录
BACKUP_DIR = Path(__file__).parent.parent / 'rules_backup'

def backup_rules(rule_dir: Path):
    """备份原始规则文件"""
    if BACKUP_DIR.exists():
        shutil.rmtree(BACKUP_DIR)
    shutil.copytree(rule_dir, BACKUP_DIR)
    print(f"已备份规则到: {BACKUP_DIR}")

def analyze_yaml_structure(file_path: Path) -> dict:
    """分析YAML文件结构，找出重复键"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    lines = content.split('\n')
    pattern_section = False
    current_pattern = None
    patterns = defaultdict(list)

    for i, line in enumerate(lines):
        stripped = line.strip()

        # 检测pattern section开始
        if stripped.startswith('pattern:'):
            pattern_section = True
            continue

        # 检测pattern section结束（遇到非缩进的顶级键）
        if pattern_section and stripped and not stripped.startswith('#') and not line.startswith('  '):
            if ':' in stripped and not stripped.endswith('|'):
                pattern_section = False
                continue

        # 收集pattern中的键值对
        if pattern_section and stripped and ':' in stripped:
            # 处理YAML注释
            if stripped.startswith('#'):
                continue

            # 解析键值对
            match = re.match(r'^(\w+):\s*[\'"]?(.+?)[\'"]?\s*$', stripped)
            if match:
                key = match.group(1)
                value = match.group(2)
                if value:
                    patterns[key].append(value)

    return dict(patterns)

def merge_patterns(patterns: list) -> str:
    """合并多个正则模式"""
    if not patterns:
        return ''

    # 去重
    unique_patterns = list(dict.fromkeys(patterns))

    # 使用非捕获组连接
    merged = '(?:' + ')|(?:'.join(unique_patterns) + ')'
    return merged

def fix_yaml_file(file_path: Path) -> bool:
    """修复单个YAML文件"""
    print(f"\n处理: {file_path.name}")

    # 分析重复键
    patterns = analyze_yaml_structure(file_path)

    has_duplicates = any(len(v) > 1 for v in patterns.values())

    if not has_duplicates:
        print(f"  无重复键，跳过")
        return False

    # 读取原始内容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 备份原始文件
    backup_file = BACKUP_DIR / file_path.name
    backup_file.write_text(content)

    # 修复重复键
    lines = content.split('\n')
    new_lines = []
    pattern_section = False
    seen_keys = set()
    pending_comments = []

    for i, line in enumerate(lines):
        stripped = line.strip()

        # 检测pattern section
        if stripped.startswith('pattern:'):
            pattern_section = True
            seen_keys = set()
            new_lines.append(line)
            continue

        # 检测pattern section结束
        if pattern_section and stripped and not stripped.startswith('#'):
            if ':' in stripped and not line.startswith('  ') and not line.startswith('\t'):
                pattern_section = False

        # 处理pattern section中的内容
        if pattern_section:
            # 保留注释
            if stripped.startswith('#'):
                pending_comments.append(line)
                continue

            # 解析键值对
            match = re.match(r'^(\s+)(\w+):\s*(.+?)\s*$', line)
            if match:
                indent, key, value = match.groups()

                # 如果是重复键，添加到已存在键的模式中
                if key in seen_keys:
                    # 找到之前该键的行索引
                    for j in range(len(new_lines) - 1, -1, -1):
                        prev_line = new_lines[j]
                        if re.match(rf'^\s+{key}:\s*', prev_line):
                            # 提取之前的值
                            prev_match = re.match(rf'^(\s+{key}:\s*[\'"]?)(.+?)([\'"]?\s*)$', prev_line)
                            if prev_match:
                                prefix = prev_match.group(1)
                                old_value = prev_match.group(2)
                                suffix = prev_match.group(3) or ''

                                # 合并值
                                if old_value.startswith('(') and old_value.endswith(')'):
                                    # 去掉外层括号
                                    old_value = old_value[1:-1]

                                if value.startswith('(') and value.endswith(')'):
                                    value = value[1:-1]

                                # 使用 | 连接
                                combined = f"({old_value}|{value})"

                                # 更新行
                                quote = "'" if "'" in prefix or "'" in suffix else ''
                                new_lines[j] = f"{prefix}{quote}{combined}{quote}{suffix}"
                            break
                    continue  # 跳过当前重复行
                else:
                    seen_keys.add(key)
                    # 添加待处理的注释
                    if pending_comments:
                        new_lines.extend(pending_comments)
                        pending_comments = []

        new_lines.append(line)

    # 写入修复后的内容
    fixed_content = '\n'.join(new_lines)

    # 验证YAML语法
    try:
        yaml.safe_load(fixed_content)
        file_path.write_text(fixed_content)
        print(f"  ✓ 已修复重复键")
        for key, values in patterns.items():
            if len(values) > 1:
                print(f"    - {key}: {len(values)}个重复 -> 合并")
        return True
    except yaml.YAMLError as e:
        print(f"  ✗ YAML语法错误: {e}")
        # 恢复备份
        file_path.write_text(content)
        return False

def main():
    rule_dir = Path(__file__).parent.parent / 'rules'

    if not rule_dir.exists():
        print(f"规则目录不存在: {rule_dir}")
        return

    # 备份原始规则
    backup_rules(rule_dir)

    # 处理所有YAML文件
    yaml_files = list(rule_dir.glob('*.yaml')) + list(rule_dir.glob('*.yml'))

    fixed_count = 0
    for yaml_file in yaml_files:
        if fix_yaml_file(yaml_file):
            fixed_count += 1

    print(f"\n{'='*50}")
    print(f"总计: 处理 {len(yaml_files)} 个文件，修复 {fixed_count} 个")
    print(f"备份位置: {BACKUP_DIR}")

if __name__ == '__main__':
    main()
