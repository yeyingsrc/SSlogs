#!/usr/bin/env python3
"""
SSlogs 自定义规则配置示例
"""
import yaml
from pathlib import Path
from core.rule_engine import RuleEngine


def create_custom_sql_injection_rule():
    """创建自定义SQL注入检测规则"""
    rule_config = {
        'name': '自定义SQL注入检测',
        'pattern': {
            'url': '(union.*select|insert.*into|delete.*from|drop.*table)',
            'user_agent': '(sqlmap|havij|nimbbang|pangolin)'
        },
        'severity': 'high',
        'category': 'sql_injection',
        'description': '检测SQL注入攻击尝试，包括常见的注入模式和扫描工具',
        'mitigation': '使用参数化查询和输入验证'
    }

    # 保存规则文件
    rules_dir = Path('rules')
    custom_rule_file = rules_dir / 'custom_sql_injection.yaml'

    with open(custom_rule_file, 'w', encoding='utf-8') as f:
        yaml.dump([rule_config], f, allow_unicode=True)

    print(f"✅ 自定义规则已创建: {custom_rule_file}")
    return custom_rule_file


def create_advanced_xss_rule():
    """创建高级XSS检测规则"""
    rule_config = {
        'name': '高级XSS攻击检测',
        'pattern': {
            'url': '(<script[^>]*>|javascript:|on\\w+\\s*=)',
            'user_agent': '(<script>|alert\\()'
        },
        'severity': 'high',
        'category': 'xss',
        'description': '检测高级XSS攻击，包括脚本标签、JavaScript协议和事件处理器',
        'examples': [
            '<script>alert(document.cookie)</script>',
            'javascript:void(0)',
            'onmouseover=alert(1)'
        ]
    }

    rules_dir = Path('rules')
    advanced_xss_file = rules_dir / 'advanced_xss.yaml'

    with open(advanced_xss_file, 'w', encoding='utf-8') as f:
        yaml.dump([rule_config], f, allow_unicode=True)

    print(f"✅ 高级XSS规则已创建: {advanced_xss_file}")
    return advanced_xss_file


def create_brute_force_rule():
    """创建暴力破解检测规则（带聚合）"""
    rule_config = {
        'name': '暴力破解检测',
        'pattern': {
            'url': '/(login|admin|signin|auth)',
            'request_method': 'POST',
            'status_code': '(401|403)'
        },
        'severity': 'medium',
        'category': 'brute_force',
        'description': '检测针对认证端点的暴力破解攻击',
        'aggregation': {
            'window': '60s',
            'group_by': ['src_ip'],
            'threshold': 10,
            'period': '30s'
        },
        'mitigation': '实施账户锁定策略和速率限制'
    }

    rules_dir = Path('rules')
    brute_force_file = rules_dir / 'brute_force.yaml'

    with open(brute_force_file, 'w', encoding='utf-8') as f:
        yaml.dump([rule_config], f, allow_unicode=True)

    print(f"✅ 暴力破解规则已创建: {brute_force_file}")
    return brute_force_file


def create_aggregation_rule():
    """创建聚合检测规则示例"""
    rule_config = {
        'name': '目录扫描检测',
        'pattern': {
            'url': '(/admin|/backup|/config|/\.env|/\.git|/wp-admin)',
            'status_code': '(200|403|404)'
        },
        'severity': 'medium',
        'category': 'reconnaissance',
        'description': '检测目录扫描和枚举攻击',
        'aggregation': {
            'window': '300s',
            'group_by': ['src_ip', 'url'],
            'threshold': 20,
            'period': '60s'
        },
        'false_positive_filter': {
            'user_agent': ['googlebot', 'bingbot', 'baiduspider']
        }
    }

    rules_dir = Path('rules')
    scanning_file = rules_dir / 'directory_scanning.yaml'

    with open(scanning_file, 'w', encoding='utf-8') as f:
        yaml.dump([rule_config], f, allow_unicode=True)

    print(f"✅ 扫描检测规则已创建: {scanning_file}")
    return scanning_file


def test_custom_rules():
    """测试自定义规则"""
    print("\n🧪 测试自定义规则...")

    try:
        # 加载规则引擎
        rule_engine = RuleEngine('rules', enable_ai_analysis=False)

        # 获取规则统计
        total_rules = len(rule_engine.rules)
        compiled_rules = len(rule_engine.compiled_rules)

        print(f"📊 规则统计:")
        print(f"  总规则数: {total_rules}")
        print(f"  编译成功: {compiled_rules}")
        print(f"  编译失败: {total_rules - compiled_rules}")

        if compiled_rules > 0:
            print("\n✅ 规则加载成功，可以开始使用")

            # 显示按类别分组的规则
            category_count = {}
            for rule in rule_engine.rules:
                category = rule.get('category', 'unknown')
                category_count[category] = category_count.get(category, 0) + 1

            print(f"\n📋 规则类别统计:")
            for category, count in sorted(category_count.items(), key=lambda x: x[1], reverse=True):
                print(f"  {category}: {count} 条规则")

    except Exception as e:
        print(f"❌ 规则测试失败: {e}")


def create_rule_template():
    """创建规则模板文件"""
    template = {
        'name': '规则名称',
        'pattern': {
            # 匹配模式 - 可以包括 url, user_agent, request_method, status_code 等
            'url': '正则表达式模式',
            'user_agent': '可选的用户代理匹配',
            'request_method': '可选的HTTP方法匹配'
        },
        'severity': 'high',  # high, medium, low, critical
        'category': 'attack_category',
        'description': '规则描述',
        'examples': ['示例日志模式1', '示例日志模式2'],
        'mitigation': '缓解措施建议',
        # 可选：聚合配置
        'aggregation': {
            'window': '时间窗口',
            'group_by': ['分组字段'],
            'threshold': 阈值,
            'period': '时间周期'
        },
        # 可选：误报过滤
        'false_positive_filter': {
            'user_agent': ['合法的用户代理列表'],
            'url': ['合法的URL模式']
        }
    }

    rules_dir = Path('rules')
    template_file = rules_dir / 'RULE_TEMPLATE.yaml'

    with open(template_file, 'w', encoding='utf-8') as f:
        yaml.dump([template], f, allow_unicode=True)

    print(f"📋 规则模板已创建: {template_file}")
    print("💡 复制此模板并修改以创建新的检测规则")

    return template_file


def rule_best_practices():
    """规则编写最佳实践"""
    print("\n📚 规则编写最佳实践:")

    practices = [
        "1. 规则命名",
        "   - 使用清晰的描述性名称",
        "   - 格式: 动作_对象_类型 (如: detect_sql_injection)",

        "2. 模式编写",
        "   - 使用正则表达式模式",
        "   - 避免过于宽泛的模式 (如 .* )",
        "   - 测试模式的匹配准确度",

        "3. 严重级别",
        "   - critical: 立即威胁 (RCE, SQL注入)",
        "   - high: 严重威胁 (XSS, CSRF)",
        "   - medium: 中等威胁 (扫描,探测)",
        "   - low: 低威胁 (信息收集)",

        "4. 分类选择",
        "   - injection: 注入攻击",
        "   - xss: 跨站脚本",
        "   - rce: 远程代码执行",
        "   - reconnaissance: 信息收集",
        "   - brute_force: 暴力破解",

        "5. 聚合配置",
        "   - window: 时间窗口 (如 60s, 5m)",
        "   - group_by: 分组字段",
        "   - threshold: 触发阈值",
        "   - period: 检查周期",

        "6. 误报控制",
        "   - 使用 false_positive_filter",
        "   - 排除已知的合法工具和爬虫",
        "   - 考虑业务上下文",

        "7. 测试验证",
        "   - 使用正常流量测试，确保无误报",
        "   - 使用攻击流量测试，确保无漏报",
        "   - 记录规则的有效性和限制"
    ]

    for practice in practices:
        print(practice)


if __name__ == '__main__':
    print("🚀 SSlogs 自定义规则配置示例")
    print("=" * 60)

    try:
        # 创建各种自定义规则
        print("1️⃣  创建SQL注入规则:")
        create_custom_sql_injection_rule()

        print("\n2️⃣  创建高级XSS规则:")
        create_advanced_xss_rule()

        print("\n3️⃣  创建暴力破解规则:")
        create_brute_force_rule()

        print("\n4️⃣  创建扫描检测规则:")
        create_aggregation_rule()

        print("\n5️⃣  创建规则模板:")
        create_rule_template()

        # 测试规则
        test_custom_rules()

        # 显示最佳实践
        rule_best_practices()

        print("\n✅ 自定义规则示例运行完成")

    except Exception as e:
        print(f"\n❌ 示例运行失败: {e}")
        import traceback
        traceback.print_exc()