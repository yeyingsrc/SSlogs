"""
规则质量回归测试。

固化 P2 阶段建立的规则质量基线：
- 否定样本（正常流量）必须零误报
- 肯定样本（攻击流量）必须命中对应 category

本测试是规则库健康的守门员：任何规则改动若引入误报或漏报，
此处的断言会立刻失败，防止回归。
"""
import pytest

from core.rule_engine import RuleEngine


@pytest.fixture(scope="module")
def engine():
    """模块级共享引擎实例，避免每个用例都重新加载规则。"""
    return RuleEngine('rules', enable_ai_analysis=False)


# ===== 否定样本：正常流量，任何规则都不应命中 =====
NORMAL_SAMPLES = [
    ("正常首页", {
        'src_ip': '192.168.1.50', 'request_path': '/index.html',
        'method': 'GET', 'user_agent': 'Mozilla/5.0', 'status_code': '200',
    }),
    ("正常登录页", {
        'src_ip': '192.168.1.50', 'request_path': '/login',
        'method': 'GET', 'user_agent': 'Mozilla/5.0', 'status_code': '200',
    }),
    ("正常分页API", {
        'src_ip': '10.0.0.5', 'request_path': '/api/users?page=1&size=20',
        'method': 'GET', 'user_agent': 'Mozilla/5.0', 'status_code': '200',
    }),
    ("正常搜索", {
        'src_ip': '10.0.0.5', 'request_path': '/search?q=hello+world',
        'method': 'GET', 'user_agent': 'Mozilla/5.0', 'status_code': '200',
    }),
    ("正常POST评论", {
        'src_ip': '10.0.0.5', 'request_path': '/api/comment',
        'method': 'POST', 'request_body': '{"text":"good post"}',
        'user_agent': 'Mozilla/5.0', 'status_code': '201',
    }),
    ("正常404", {
        'src_ip': '203.0.113.1', 'request_path': '/missing-page',
        'method': 'GET', 'user_agent': 'Mozilla/5.0', 'status_code': '404',
    }),
    ("Chrome浏览器UA", {
        'src_ip': '203.0.113.1', 'request_path': '/about',
        'method': 'GET',
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0',
        'status_code': '200',
    }),
]


# ===== 肯定样本：攻击流量，必须命中对应 category =====
ATTACK_SAMPLES = [
    ("SQL注入", {
        'src_ip': '198.51.100.1', 'request_path': '/?id=1 union select * from users',
        'method': 'GET', 'user_agent': 'Mozilla/5.0', 'status_code': '200',
    }, 'sql_injection'),
    ("XSS脚本注入", {
        'src_ip': '198.51.100.1', 'request_path': '/?q=<script>alert(1)</script>',
        'method': 'GET', 'user_agent': 'Mozilla/5.0', 'status_code': '200',
    }, 'xss'),
    ("命令注入", {
        'src_ip': '198.51.100.1', 'request_path': '/?cmd=;id;whoami',
        'method': 'GET', 'user_agent': 'Mozilla/5.0', 'status_code': '200',
    }, 'command_injection'),
    ("路径遍历", {
        'src_ip': '198.51.100.1', 'request_path': '/?file=../../../etc/passwd',
        'method': 'GET', 'user_agent': 'Mozilla/5.0', 'status_code': '200',
    }, 'path_traversal'),
    ("nikto扫描器", {
        'src_ip': '198.51.100.1', 'request_path': '/',
        'method': 'GET', 'user_agent': 'Nikto/2.5', 'status_code': '200',
    }, 'reconnaissance'),
    ("phpmyadmin探测", {
        'src_ip': '198.51.100.1', 'request_path': '/phpmyadmin/',
        'method': 'GET', 'user_agent': 'Mozilla/5.0', 'status_code': '404',
    }, 'reconnaissance'),
]


def _non_agg_matches(engine, entry):
    """返回单行（非聚合）匹配的 category 集合。"""
    engine.reset_aggregation()
    return {
        m['rule'].get('category')
        for m in engine.match_log(entry)
        if not m['match_details'].get('aggregated')
    }


class TestNoFalsePositives:
    """正常流量不得触发任何单行规则。"""

    @pytest.mark.parametrize("label,entry", NORMAL_SAMPLES,
                             ids=[s[0] for s in NORMAL_SAMPLES])
    def test_normal_traffic_no_alert(self, engine, label, entry):
        cats = _non_agg_matches(engine, entry)
        assert cats == set(), \
            f"[误报] 正常流量「{label}」命中了: {cats}"


class TestNoFalseNegatives:
    """攻击流量必须命中对应的 category。"""

    @pytest.mark.parametrize("label,entry,expected_cat", ATTACK_SAMPLES,
                             ids=[s[0] for s in ATTACK_SAMPLES])
    def test_attack_detected(self, engine, label, entry, expected_cat):
        cats = _non_agg_matches(engine, entry)
        assert expected_cat in cats, \
            f"[漏报] 攻击「{label}」未命中 {expected_cat}，实际命中: {cats}"


class TestRuleLibraryHealth:
    """规则库整体健康度：加载零丢弃。"""

    def test_all_rules_compiled(self, engine):
        """所有加载的规则都必须成功编译，不允许静默丢弃。"""
        dropped = len(engine.rules) - len(engine.compiled_rules)
        assert dropped == 0, \
            f"{dropped} 条规则编译失败被静默丢弃（应修复其YAML或正则）"

    def test_brute_force_is_aggregation(self, engine):
        """暴力破解应为聚合规则，单次登录不触发。"""
        bf = [r for r in engine.rules if r.get('aggregation_only')
              and r.get('category') == 'brute_force']
        assert len(bf) >= 1, "聚合版暴力破解规则缺失"

    def test_no_wildcard_star_only_patterns(self, engine):
        """禁止 src_ip:'.*' 这种匹配一切的退化正则。

        聚合规则(aggregation_only)的 pattern 仅是占位、不参与单行匹配，故跳过。
        """
        offenders = []
        for r in engine.rules:
            if r.get('aggregation_only'):
                continue  # 聚合规则的 pattern 是占位，不参与匹配
            pat = r.get('pattern', {})
            if isinstance(pat, dict):
                for k, v in pat.items():
                    if isinstance(v, str) and v.strip() in ('.*', '.+', '.*$'):
                        offenders.append(f"{r.get('source_file')}:{k}={v!r}")
        assert not offenders, \
            f"发现退化通配正则（会匹配一切导致全量误报）: {offenders}"
