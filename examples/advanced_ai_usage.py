#!/usr/bin/env python3
"""
SSlogs 高级AI分析示例
"""
import yaml
from core.parser import LogParser
from core.ai_analyzer import AIAnalyzer
from core.rule_engine import RuleEngine


def advanced_ai_analysis():
    """高级AI分析示例"""
    # 1. 创建配置
    config = {
        'log_path': 'logs/*.log',
        'log_format': {
            'type': 'web',
            'fields': {
                'src_ip': r'(\d+\.\d+\.\d+\.\d+)',
                'timestamp': r'\[(.*?)\]',
                'request_line': r'"([A-Z]+\s+[^\s]+\s+HTTP/[\d\.]+)"',
                'status_code': r'"\s+(\d{3})\s+',
                'user_agent': r'"([^"]*)"'
            }
        },
        'rule_dir': 'rules',
        'output_dir': 'output',
        'ai': {
            'type': 'cloud',
            'cloud_provider': 'deepseek'
        },
        'deepseek': {
            'api_key': 'your-api-key',  # 替换为实际API密钥
            'model': 'deepseek-ai/DeepSeek-V3',
            'base_url': 'https://api.siliconflow.cn/v1/chat/completions',
            'timeout': 30,
            'max_tokens': 2048
        },
        'ai_analysis': {
            'high_risk_only': True,
            'successful_attacks_only': True,
            'max_ai_analysis': 3
        }
    }

    # 2. 初始化AI分析器
    try:
        ai_analyzer = AIAnalyzer('config.yaml')
        print("✅ AI分析器初始化成功")
    except Exception as e:
        print(f"⚠️  AI分析器初始化失败: {e}")
        print("💡 请检查配置文件或API密钥")
        return

    # 3. 示例攻击日志
    attack_logs = {
        'sql_injection': {
            'context': '''198.51.100.1 - - [25/Dec/2023:10:00:00 +0000] "GET /user?id=1 union select * from users HTTP/1.1" 200 1234 "Mozilla/5.0"
''',
            'category': 'injection',
            'name': 'SQL注入攻击',
            'threat_score': 8.5
        },
        'xss_attack': {
            'context': '''198.51.100.1 - - [25/Dec/2023:10:01:00 +0000] "GET /search?q=<script>alert(1)</script> HTTP/1.1" 200 567 "Mozilla/5.0"
''',
            'category': 'xss',
            'name': 'XSS跨站脚本攻击',
            'threat_score': 7.2
        },
        'command_injection': {
            'context': '''198.51.100.1 - - [25/Dec/2023:10:02:00 +0000] "POST /upload&cmd=whoami HTTP/1.1" 200 890 "curl/7.68.0"
''',
            'category': 'rce',
            'name': '远程命令执行',
            'threat_score': 9.8
        }
    }

    # 4. 对每种攻击进行AI分析
    print("\n🤖 开始AI深度分析...")

    for attack_type, attack_data in attack_logs.items():
        print(f"\n🎯 分析 {attack_type}:")

        try:
            # 使用专用分析模板
            analysis_result = ai_analyzer.analyze_log(
                log_context=attack_data['context'],
                attack_category=attack_data['category'],
                attack_name=attack_data['name'],
                threat_score=attack_data['threat_score']
            )

            print(f"📊 威胁评分: {attack_data['threat_score']}/10.0")
            print(f"\n🤖 AI分析结果:")
            print("-" * 60)
            print(analysis_result)
            print("-" * 60)

        except Exception as e:
            print(f"⚠️  AI分析失败: {e}")
            print("💡 使用备用分析机制")

    # 5. 演示不同的AI服务提供者
    print("\n🔄 AI服务提供者演示:")

    ai_providers = [
        ('cloud', 'deepseek'),
        ('local', 'ollama')
    ]

    for ai_type, provider in ai_providers:
        print(f"\n📡 测试 {ai_type} - {provider}:")

        try:
            # 这里只是演示，实际使用时需要相应的服务可用
            if ai_type == 'local':
                print("💡 本地AI服务需要Ollama运行在 localhost:11434")
            else:
                print("💡 云端AI服务需要有效的API密钥")
        except Exception as e:
            print(f"⚠️  服务不可用: {e}")


def ai_analysis_with_fallback():
    """AI分析降级策略示例"""
    print("🤖 AI分析降级策略演示")

    # 创建AI分析器（使用测试配置）
    ai_analyzer = AIAnalyzer('config.yaml')

    # 测试日志上下文
    test_context = '''192.168.1.100 - - [25/Dec/2023:10:00:00 +0000] "GET /admin/config HTTP/1.1" 200 1234'''

    # 尝试AI分析
    print("📡 尝试AI分析...")

    try:
        result = ai_analyzer.analyze_log(
            log_context=test_context,
            attack_category='reconnaissance',
            threat_score=6.5
        )

        if "AI分析失败" not in result and "本地AI分析失败" not in result:
            print("✅ AI分析成功")
            print(f"\n🤖 分析结果:")
            print(result)
        else:
            print("⚠️  AI分析返回错误信息")
            print("💡 这表明使用了备用分析机制")

    except Exception as e:
        print(f"❌ AI分析异常: {e}")
        print("💡 系统会自动使用备用分析")


def specialized_attack_prompts():
    """专用攻击提示词示例"""
    print("🎯 专用攻击分析提示词演示")

    ai_analyzer = AIAnalyzer('config.yaml')

    # 不同攻击类型的专用提示词
    attack_scenarios = [
        ('injection', '数据库注入攻击'),
        ('xss', '跨站脚本攻击'),
        ('rce', '远程代码执行'),
        ('ssrf', '服务器端请求伪造'),
        ('api_security', 'API安全威胁'),
        ('cloud_security', '云原生安全')
    ]

    print("\n📋 支持的专用攻击类型:")

    for category, description in attack_scenarios:
        # 生成专用提示词
        prompt = ai_analyzer._get_attack_specific_prompt(
            log_context="示例日志内容",
            attack_category=category
        )

        print(f"\n✅ {category}: {description}")
        print(f"   提示词长度: {len(prompt)} 字符")
        print(f"   关键词: {description.split(' ')[1]}")

    print("\n💡 每种攻击类型都有专门的分析模板:")
    print("   - SQL注入: 数据库安全专家视角")
    print("   - XSS攻击: Web应用安全专家视角")
    print("   - RCE攻击: 系统安全专家视角")
    print("   - SSRF攻击: 网络安全专家视角")


if __name__ == '__main__':
    print("🚀 SSlogs 高级AI分析示例")
    print("=" * 60)

    try:
        # 运行高级AI分析
        advanced_ai_analysis()

        # 演示降级策略
        print("\n" + "=" * 60)
        ai_analysis_with_fallback()

        # 演示专用提示词
        print("\n" + "=" * 60)
        specialized_attack_prompts()

        print("\n✅ 高级示例运行完成")

    except Exception as e:
        print(f"\n❌ 示例运行失败: {e}")
        import traceback
        traceback.print_exc()