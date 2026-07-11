"""临时工具：修复规则文件 pattern 段中"同键重复"导致的 YAML 解析失败。

针对 SSlogs 规则库中 12 个文件共有的问题：
  pattern:
    request_body: '正则A'
    request_body: '正则B'   # YAML 不允许同键重复 → 解析失败

修复策略：把同一字段键下的多个正则用 | 合并为一个正则，保留全部检测能力。
同时处理正则中含单引号 ' 的情况（改用双引号 YAML 字符串并双写反斜杠）。

用法: python scripts/fix_rule_yaml.py rules/<file>.yaml [--dry-run]
"""
import re
import sys


def extract_pattern_block(lines):
    """返回 (pattern 起始行号, pattern 段行列表, 后续行列表)。"""
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith('pattern:'):
            start = i
            break
    if start is None:
        return None, [], lines
    body = []
    rest_start = start + 1
    for j in range(start + 1, len(lines)):
        # 顶格行表示 pattern 段结束
        if lines[j] and not lines[j].startswith(' ') and not lines[j].startswith('\t') and lines[j].strip():
            rest_start = j
            break
        body.append(lines[j])
    else:
        rest_start = len(lines)
    return start, body, lines[rest_start:]


def parse_field_regex(body):
    """从 pattern 段提取 (字段键, 正则原始值) 列表，保留顺序。

    支持：
      field: 'regex'
      field: "regex"
      field:
        'regex1'   # 多行裸字符串（ai_ml 风格）
        'regex2'
    """
    items = []
    current_key = None
    for ln in body:
        stripped = ln.strip()
        if not stripped or stripped.startswith('#'):
            continue
        # 两空格缩进的键: 形如 "  field: ..."
        m = re.match(r'^\s{2}(\w+):\s*(.*)$', ln)
        if m:
            key = m.group(1)
            rest = m.group(2).strip()
            if rest and not rest.startswith('#'):
                # 单行 键: 值
                regex = extract_regex_value(rest)
                if regex is not None:
                    items.append((key, regex))
                    current_key = key
                else:
                    current_key = key  # 键后无值(多行风格)
            else:
                current_key = key  # 只有键, 值在后续行
        else:
            # 更深缩进的裸字符串行（多行风格）
            mr = re.match(r"^\s{4,}['\"](.*)['\"]\s*(#.*)?$", ln)
            if mr and current_key:
                items.append((current_key, mr.group(1)))
    return items


def extract_regex_value(text):
    """从 'regex' 或 "regex" 或 regex 中提取正则内容。"""
    text = text.strip()
    if (text.startswith("'") and text.endswith("'")) or (text.startswith('"') and text.endswith('"')):
        return text[1:-1]
    if text.startswith("'") or text.startswith('"'):
        # 不完整引号（单引号转义问题）— 取首个引号到行尾
        q = text[0]
        return text[1:]
    if text and not text.startswith('#'):
        return text
    return None


def yaml_quote_regex(regex):
    """安全地把正则包成 YAML 字符串。

    含单引号 ' 的正则用双引号(并把 \\ 双写)，否则用单引号。
    """
    if "'" in regex:
        # 双引号 YAML: 反斜杠需双写, 双引号需转义
        escaped = regex.replace('\\', '\\\\').replace('"', '\\"')
        return f'"{escaped}"'
    else:
        return f"'{regex}'"


def merge(items):
    """把同键的多个正则用 | 合并，保持顺序、去重。"""
    merged = {}
    order = []
    for key, regex in items:
        if key not in merged:
            merged[key] = []
            order.append(key)
        merged[key].append(regex)
    result = []
    for key in order:
        regexes = merged[key]
        if len(regexes) == 1:
            result.append((key, regexes[0]))
        else:
            # 用 (?:...|...) 合并, 避免破坏原有分组优先级
            combined = '|'.join(f'(?:{r})' for r in regexes)
            result.append((key, combined))
    return result


def fix_file(path, dry_run=False):
    with open(path, encoding='utf-8') as f:
        lines = f.readlines()
    start, body, rest = extract_pattern_block(lines)
    if start is None:
        print(f"[跳过] {path}: 无 pattern 段")
        return False
    items = parse_field_regex(body)
    if not items:
        print(f"[跳过] {path}: pattern 段无可解析项")
        return False
    merged = merge(items)

    # 重建 pattern 段
    new_body = ['pattern:\n']
    for key, regex in merged:
        new_body.append(f'  {key}: {yaml_quote_regex(regex)}\n')
    # pattern 段后空一行(若原文件有)
    if body and body[-1].strip() == '':
        new_body.append('\n')

    new_lines = lines[:start] + new_body + ['\n'] + rest
    # 去除可能重复的空行
    out = []
    prev_blank = False
    for ln in new_lines:
        is_blank = ln.strip() == ''
        if is_blank and prev_blank:
            continue
        out.append(ln)
        prev_blank = is_blank

    if dry_run:
        print(f"[DRY-RUN] {path} 修复后 pattern 段:")
        print(''.join(new_body))
        return True
    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(out)
    print(f"[已修复] {path}: 合并为 {len(merged)} 个键")
    return True


if __name__ == '__main__':
    args = sys.argv[1:]
    dry = '--dry-run' in args
    files = [a for a in args if not a.startswith('--')]
    for fp in files:
        fix_file(fp, dry_run=dry)
