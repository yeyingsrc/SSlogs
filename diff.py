# AI驱动的代码差异分析与POC生成器（支持硅基流动 API）

"""
工具目标：
1. 分析两个代码版本的差异（diff/patch）。
2. 使用AI模型分析差异是否涉及安全漏洞修复。
3. 自动生成概念验证（Proof of Concept, PoC）代码。
4. 支持命令行参数调用，适合作为CLI工具使用。
"""

import difflib
import argparse
import requests
import os

# === 配置硅基流动API参数 ===
SILICON_API_URL = "https://api.siliconflow.cn/v1/chat/completions"
SILICON_API_KEY = os.getenv("SILICON_API_KEY")  # 你需要先在环境变量中设置密钥
MODEL_NAME = "siliconflow/gpt4-secure"  # 示例模型名，根据平台确认


def call_silicon_api(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {SILICON_API_KEY}",
        "Content-Type": "application/json"
    }
    json_data = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }
    response = requests.post(SILICON_API_URL, headers=headers, json=json_data)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        raise Exception(f"[!] API请求失败：{response.status_code}: {response.text}")


def diff_code(old_code: str, new_code: str) -> str:
    old_lines = old_code.splitlines(keepends=True)
    new_lines = new_code.splitlines(keepends=True)
    diff = list(difflib.unified_diff(old_lines, new_lines, fromfile='old', tofile='new'))
    return ''.join(diff)


def analyze_patch_with_ai(diff_text: str) -> str:
    prompt = f"""
你是一个安全分析专家。下面是一个代码补丁diff，请判断该补丁是否为安全漏洞修复，并分析其修复了什么问题（如缓冲区溢出、SQL注入、权限绕过等）。

```diff
{diff_text}
```

请输出漏洞描述。
"""
    return call_silicon_api(prompt)


def generate_poc_with_ai(diff_text: str, vulnerability_desc: str) -> str:
    prompt = f"""
基于以下补丁差异和漏洞描述，请生成一个最小化的概念验证（PoC）代码，演示该漏洞被利用的方式。

漏洞描述:
{vulnerability_desc}

补丁差异:
```diff
{diff_text}
```

请直接输出完整PoC代码。
"""
    return call_silicon_api(prompt)


def main():
    parser = argparse.ArgumentParser(description="AI驱动的代码差异分析与PoC生成器（支持硅基流动API）")
    parser.add_argument("old", help="旧版本代码路径")
    parser.add_argument("new", help="新版本代码路径")
    args = parser.parse_args()

    with open(args.old, 'r') as f:
        old_code = f.read()
    with open(args.new, 'r') as f:
        new_code = f.read()

    print("[*] 正在计算diff...")
    diff_text = diff_code(old_code, new_code)
    print("[*] 代码差异:\n", diff_text)

    print("[*] 正在调用AI分析补丁是否为安全修复...")
    vuln_desc = analyze_patch_with_ai(diff_text)
    print("[*] 漏洞分析:\n", vuln_desc)

    print("[*] 正在生成PoC...")
    poc_code = generate_poc_with_ai(diff_text, vuln_desc)
    print("[*] 生成的PoC:\n", poc_code)


if __name__ == '__main__':
    if not SILICON_API_KEY:
        print("[!] 请先设置环境变量 SILICON_API_KEY")
        exit(1)
    main()
