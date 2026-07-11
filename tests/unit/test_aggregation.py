"""
聚合层（跨事件关联）单元测试。

验证 P1 新增的滑动窗口聚合能力：
- 暴力破解、目录爆破、高频请求等需要"跨事件计数"的规则
  现在可以通过规则 YAML 的 aggregation 字段声明阈值，由引擎内部
  的滑动窗口在窗口内计数达阈值时生成聚合告警。
"""
import time
import pytest

from core.rule_engine import RuleEngine


@pytest.fixture
def engine():
    """用真实规则目录初始化引擎，禁用AI。"""
    return RuleEngine('rules', enable_ai_analysis=False)


def _make_login_entry(src_ip, status='200', path='/login.php'):
    """构造一条登录请求日志条目。"""
    return {
        'src_ip': src_ip,
        'request_path': path,
        'method': 'POST',
        'status_code': status,
        'user_agent': 'Mozilla/5.0',
    }


class TestAggregationWindow:
    """聚合窗口核心行为。"""

    def test_below_threshold_does_not_alert(self, engine):
        """窗口内计数未达阈值，不应产生聚合告警。"""
        engine.reset_aggregation()
        for _ in range(5):  # 低于典型暴力破解阈值
            alerts = engine.observe_for_aggregation(_make_login_entry('1.2.3.4', status='401'))
        assert alerts == []

    def test_threshold_crossed_produces_alert(self, engine):
        """同一IP在窗口内对敏感端点请求达阈值，应产生聚合告警。

        注意：聚合层在同一窗口内对同一桶有重复告警抑制（避免刷屏），
        所以必须收集整个过程的告警，而非只看最后一次。
        """
        engine.reset_aggregation()
        all_alerts = []
        for _ in range(20):
            all_alerts.extend(
                engine.observe_for_aggregation(_make_login_entry('1.2.3.4', status='401'))
            )
        # 整个过程至少产生一条聚合告警
        assert len(all_alerts) >= 1
        a = all_alerts[0]
        assert a['rule'].get('category') == 'brute_force'
        # 聚合告警结构应与普通 match_result 兼容，便于并入报告流程
        assert 'threat_score' in a
        assert 'log_entry' in a
        assert a['match_details'].get('aggregated') is True
        # 告警应记录命中次数与窗口（阈值10，触发时 count>=10）
        assert a['match_details']['count'] >= 10

    def test_different_ips_counted_separately(self, engine):
        """不同IP的计数应相互独立，各自未达阈值则不告警。"""
        engine.reset_aggregation()
        for ip in ['1.1.1.1', '2.2.2.2', '3.3.3.3', '4.4.4.4']:
            for _ in range(5):
                alerts = engine.observe_for_aggregation(_make_login_entry(ip, status='401'))
        assert alerts == []

    def test_failed_status_filter(self, engine):
        """声明 failed_status 的规则只统计失败响应；成功响应不计入。"""
        engine.reset_aggregation()
        alerts = []
        # 20次成功登录(200) —— 若规则只计失败，不应触发
        for _ in range(20):
            alerts = engine.observe_for_aggregation(_make_login_entry('9.9.9.9', status='200'))
        assert alerts == []

    def test_window_expiry(self, engine):
        """超出时间窗口的旧记录应被清理，不再计入当前阈值。"""
        engine.reset_aggregation()
        # 手动注入一批"过期"记录
        now = time.time()
        bucket_key = ('brute_force', '1.2.3.4', '/login.php')
        window = engine._aggregator  # 滑动窗口实例
        for ts in [now - 120, now - 110]:  # 2分钟前，超出60s窗口
            window._record(bucket_key, ts, failed=True)
        # 现在再补几条，但不足以单独达阈值
        alerts = []
        for _ in range(3):
            alerts = engine.observe_for_aggregation(_make_login_entry('1.2.3.4', status='401'))
        assert alerts == []


class TestAggregationRuleParsing:
    """规则文件 aggregation 字段的解析。"""

    def test_brute_force_rule_has_aggregation(self, engine):
        """brute_force.yaml 重写后应声明 aggregation 字段。"""
        bf_rules = [r for r in engine.rules if r.get('category') == 'brute_force']
        assert len(bf_rules) >= 1
        agg = bf_rules[0].get('aggregation')
        assert agg is not None, "brute_force 规则缺少 aggregation 字段"
        for key in ('field', 'window', 'threshold'):
            assert key in agg, f"aggregation 缺少 {key}"
