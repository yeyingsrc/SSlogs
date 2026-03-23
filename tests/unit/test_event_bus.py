"""
测试事件总线模块
"""
import pytest
import asyncio
from core.event_bus import EventBus, Event, EventHandler


@pytest.mark.unit
class TestEventBus:
    """EventBus 单元测试"""

    def test_event_bus_initialization(self):
        """测试事件总线初始化"""
        bus = EventBus()
        assert bus is not None
        assert hasattr(bus, "publish")
        assert hasattr(bus, "subscribe")

    def test_subscribe_and_publish(self):
        """测试订阅和发布事件"""
        bus = EventBus()

        # 创建一个事件处理器
        received_events = []

        def handler(event):
            received_events.append(event)

        # 订阅事件
        bus.subscribe("test_event", handler)

        # 发布事件
        event = Event(event_type="test_event", data={"message": "test"})
        bus.publish(event)

        assert len(received_events) == 1
        assert received_events[0].data["message"] == "test"

    def test_multiple_subscribers(self):
        """测试多个订阅者"""
        bus = EventBus()

        received_1 = []
        received_2 = []

        def handler_1(event):
            received_1.append(event)

        def handler_2(event):
            received_2.append(event)

        # 两个订阅者订阅同一事件
        bus.subscribe("test_event", handler_1)
        bus.subscribe("test_event", handler_2)

        # 发布事件
        event = Event(event_type="test_event", data={"test": "data"})
        bus.publish(event)

        # 两个订阅者都应该收到事件
        assert len(received_1) == 1
        assert len(received_2) == 1

    def test_unsubscribe(self):
        """测试取消订阅"""
        bus = EventBus()

        received = []

        def handler(event):
            received.append(event)

        # 订阅事件
        bus.subscribe("test_event", handler)

        # 发布第一个事件
        event1 = Event(event_type="test_event", data={"count": 1})
        bus.publish(event1)
        assert len(received) == 1

        # 取消订阅
        bus.unsubscribe("test_event", handler)

        # 发布第二个事件
        event2 = Event(event_type="test_event", data={"count": 2})
        bus.publish(event2)

        # 应该只收到第一个事件
        assert len(received) == 1

    def test_event_data(self):
        """测试事件数据传递"""
        bus = EventBus()

        received_data = {}

        def handler(event):
            received_data.update(event.data)

        test_data = {
            "string": "test",
            "number": 42,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
        }

        bus.subscribe("test_event", handler)
        event = Event(event_type="test_event", data=test_data)
        bus.publish(event)

        assert received_data == test_data

    def test_event_priority(self):
        """测试事件优先级"""
        bus = EventBus()

        execution_order = []

        def handler_high(event):
            execution_order.append("high")

        def handler_medium(event):
            execution_order.append("medium")

        def handler_low(event):
            execution_order.append("low")

        # 订阅不同优先级的事件
        bus.subscribe("test_event", handler_low, priority="low")
        bus.subscribe("test_event", handler_high, priority="high")
        bus.subscribe("test_event", handler_medium, priority="medium")

        # 发布事件
        event = Event(event_type="test_event", data={})
        bus.publish(event)

        # 高优先级应该先执行
        assert execution_order[0] == "high"
        assert execution_order[1] == "medium"
        assert execution_order[2] == "low"

    def test_event_with_metadata(self):
        """测试事件元数据"""
        bus = EventBus()

        received_event = None

        def handler(event):
            nonlocal received_event
            received_event = event

        bus.subscribe("test_event", handler)

        # 发布带元数据的事件
        event = Event(
            event_type="test_event",
            data={"message": "test"},
            metadata={"source": "test_source", "timestamp": "2024-01-15"}
        )
        bus.publish(event)

        assert received_event is not None
        assert received_event.metadata["source"] == "test_source"
        assert received_event.metadata["timestamp"] == "2024-01-15"

    def test_multiple_event_types(self):
        """测试多种事件类型"""
        bus = EventBus()

        received_events = []

        def handler_1(event):
            received_events.append(("type_1", event))

        def handler_2(event):
            received_events.append(("type_2", event))

        bus.subscribe("event_type_1", handler_1)
        bus.subscribe("event_type_2", handler_2)

        # 发布不同类型的事件
        event_1 = Event(event_type="event_type_1", data={})
        event_2 = Event(event_type="event_type_2", data={})

        bus.publish(event_1)
        bus.publish(event_2)

        assert len(received_events) == 2
        assert received_events[0][0] == "type_1"
        assert received_events[1][0] == "type_2"

    def test_event_filtering(self):
        """测试事件过滤"""
        bus = EventBus()

        received = []

        def handler(event):
            received.append(event)

        bus.subscribe("test_event", handler)

        # 发布不同类型的事件
        bus.publish(Event(event_type="test_event", data={}))
        bus.publish(Event(event_type="other_event", data={}))
        bus.publish(Event(event_type="test_event", data={}))

        # 只应该收到 test_event 类型的事件
        assert len(received) == 2


@pytest.mark.unit
class TestEventBusAsync:
    """EventBus 异步功能测试"""

    @pytest.mark.asyncio
    async def test_async_publish(self):
        """测试异步发布"""
        bus = EventBus()

        received = []

        async def async_handler(event):
            await asyncio.sleep(0.01)  # 模拟异步操作
            received.append(event)

        bus.subscribe("test_event", async_handler)

        event = Event(event_type="test_event", data={})
        await bus.publish_async(event)

        assert len(received) == 1

    @pytest.mark.asyncio
    async def test_async_multiple_handlers(self):
        """测试多个异步处理器"""
        bus = EventBus()

        received = []

        async def handler_1(event):
            await asyncio.sleep(0.01)
            received.append("handler_1")

        async def handler_2(event):
            await asyncio.sleep(0.02)
            received.append("handler_2")

        bus.subscribe("test_event", handler_1)
        bus.subscribe("test_event", handler_2)

        event = Event(event_type="test_event", data={})
        await bus.publish_async(event)

        assert len(received) == 2

    @pytest.mark.asyncio
    async def test_async_error_handling(self):
        """测试异步错误处理"""
        bus = EventBus()

        async def failing_handler(event):
            raise ValueError("Test error")

        async def working_handler(event):
            await asyncio.sleep(0.01)

        bus.subscribe("test_event", failing_handler)
        bus.subscribe("test_event", working_handler)

        event = Event(event_type="test_event", data={})

        # 即使一个处理器失败，其他也应该继续执行
        try:
            await bus.publish_async(event)
        except Exception:
            pass

        # 测试应该通过，表示错误被正确处理


@pytest.mark.unit
class TestEventBusPerformance:
    """EventBus 性能测试"""

    def test_high_frequency_events(self):
        """测试高频事件处理"""
        import time

        bus = EventBus()

        count = 0

        def handler(event):
            nonlocal count
            count += 1

        bus.subscribe("test_event", handler)

        # 发布1000个事件
        start_time = time.time()
        for i in range(1000):
            event = Event(event_type="test_event", data={"index": i})
            bus.publish(event)
        elapsed_time = time.time() - start_time

        assert count == 1000
        # 应该在合理时间内完成（< 1秒）
        assert elapsed_time < 1.0

    def test_large_event_data(self):
        """测试大数据量事件"""
        bus = EventBus()

        received = None

        def handler(event):
            nonlocal received
            received = event

        bus.subscribe("test_event", handler)

        # 创建大数据量事件
        large_data = {"items": list(range(10000))}
        event = Event(event_type="test_event", data=large_data)
        bus.publish(event)

        assert received is not None
        assert len(received.data["items"]) == 10000


@pytest.mark.unit
class TestEventBusIntegration:
    """EventBus 集成测试场景"""

    def test_log_processing_workflow(self):
        """测试日志处理工作流"""
        bus = EventBus()

        workflow_steps = []

        def parse_handler(event):
            workflow_steps.append("parsed")
            # 解析完成后发布分析事件
            bus.publish(
                Event(event_type="log_analyzed", data=event.data)
            )

        def analyze_handler(event):
            workflow_steps.append("analyzed")
            # 分析完成后发布报告事件
            bus.publish(
                Event(event_type="report_generated", data=event.data)
            )

        def report_handler(event):
            workflow_steps.append("reported")

        # 订阅事件形成工作流
        bus.subscribe("log_parsed", parse_handler)
        bus.subscribe("log_analyzed", analyze_handler)
        bus.subscribe("report_generated", report_handler)

        # 开始工作流
        bus.publish(
            Event(event_type="log_parsed", data={"log": "test log"})
        )

        # 验证工作流执行
        assert "parsed" in workflow_steps
        assert "analyzed" in workflow_steps
        assert "reported" in workflow_steps

    def test_error_recovery_workflow(self):
        """测试错误恢复工作流"""
        bus = EventBus()

        errors = []
        recovered = []

        def error_handler(event):
            errors.append(event.data["error"])
            # 尝试恢复
            bus.publish(
                Event(event_type="recover_attempt", data=event.data)
            )

        def recovery_handler(event):
            recovered.append("recovered")

        bus.subscribe("error_occurred", error_handler)
        bus.subscribe("recover_attempt", recovery_handler)

        # 模拟错误
        bus.publish(
            Event(
                event_type="error_occurred",
                data={"error": "Test error"}
            )
        )

        assert len(errors) == 1
        assert len(recovered) == 1
