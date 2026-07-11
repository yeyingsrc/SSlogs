#!/bin/bash
# 性能基准测试运行脚本

echo "🚀 SSlogs 性能基准测试"
echo "================================"

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未找到"
    exit 1
fi

# 创建必要的目录
mkdir -p tests/benchmark

# 运行性能基准测试
python3 tests/benchmark/performance_benchmark.py

echo ""
echo "💡 提示："
echo "  - 首次运行将建立性能基线"
echo "  - 后续运行将与基线比较，检测性能回归"
echo "  - 使用 --help 查看更多选项"