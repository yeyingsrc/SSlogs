# SSlogs 规则测试框架

## 📋 概述

SSlogs 规则测试框架是一个全面的测试工具，用于验证新创建的检测规则的可用性和准确性。该框架包含以下核心功能：

- 🧪 **自动化测试**: 自动生成测试数据并执行规则匹配
- 📊 **结果验证**: 多维度验证测试结果的准确性
- 📄 **报告生成**: 生成详细的HTML测试报告
- 🎯 **规则覆盖**: 确保所有新规则都能正确检测威胁

## 🏗️ 测试框架结构

```
tests/
├── test_framework.py          # 核心测试框架
├── run_tests.py              # 测试运行脚本
├── result_validator.py       # 结果验证器
├── run_all_tests.sh          # 一键测试脚本
├── README.md                 # 使用说明
├── test_data/                # 测试数据目录
│   ├── ai_ml_anomaly_test_logs.json
│   ├── threat_intelligence_test_logs.json
│   └── ...
├── results/                  # 测试结果目录
│   ├── test_results_20240115_143022.json
│   └── validation_report_20240115_143025.json
└── reports/                  # 测试报告目录
    └── test_report_20240115_143028.html
```

## 🚀 快速开始

### 一键运行测试

```bash
# 运行完整测试流程
./tests/run_all_tests.sh

# 查看帮助信息
./tests/run_all_tests.sh --help
```

### 分步骤运行

```bash
# 1. 生成测试数据
python3 tests/run_tests.py --generate-data

# 2. 运行规则测试
python3 tests/run_tests.py --run-tests

# 3. 验证测试结果
python3 tests/result_validator.py

# 4. 生成测试报告
python3 tests/run_tests.py --generate-report
```

## 📊 测试覆盖的规则类别

| 测试类别 | 规则文件 | 测试场景数 | 主要检测能力 |
|---------|----------|-----------|-------------|
| AI/ML异常检测 | `ai_ml_anomaly_detection.yaml` | 3 | 异常行为模式识别 |
| 威胁情报集成 | `threat_intelligence_integration.yaml` | 3 | IOC匹配和APT检测 |
| 零信任架构 | `zero_trust_architecture.yaml` | 3 | 身份验证和访问控制 |
| 供应链安全 | `supply_chain_security.yaml` | 3 | 软件组件和CI/CD安全 |
| 云原生威胁 | `cloud_native_advanced_threats.yaml` | 3 | Kubernetes和容器安全 |
| 隐私合规 | `privacy_compliance_detection.yaml` | 3 | GDPR/HIPAA/COPPA检测 |
| 金融安全 | `financial_industry_security.yaml` | 3 | 支付系统和反洗钱 |
| 用户行为分析 | `user_behavior_analysis.yaml` | 3 | UEBA和内部威胁 |
| 攻击链关联 | `attack_chain_correlation.yaml` | 3 | MITRE ATT&CK框架 |
| 自动化响应 | `automated_response_triggers.yaml` | 3 | 智能化威胁处置 |

## 🧪 测试场景详解

### 1. AI/ML异常检测测试
- **异常User-Agent检测**: 识别自动化工具和机器人
- **高频访问模式**: 检测异常的请求频率
- **会话行为异常**: 识别会话劫持和设备指纹变更

### 2. 威胁情报集成测试
- **恶意IP访问**: 使用已知恶意IP地址测试
- **攻击工具识别**: 测试sqlmap等工具的检测
- **APT组织特征**: 模拟Cobalt Strike等APT工具

### 3. 零信任架构测试
- **MFA绕过尝试**: 测试多因子认证绕过检测
- **权限提升检测**: 模拟权限提升攻击
- **地理位置异常**: 测试异常地理位置访问

### 4. 供应链安全测试
- **恶意依赖包**: 测试恶意npm包检测
- **容器镜像攻击**: 模拟恶意Docker镜像
- **CI/CD管道攻击**: 测试构建流程威胁

### 5. 云原生威胁测试
- **Kubernetes RBAC**: 测试K8s权限提升
- **容器逃逸**: 模拟容器逃逸尝试
- **云元数据攻击**: 测试元数据服务访问

### 6. 隐私合规测试
- **GDPR违规**: 测试个人数据访问违规
- **PII数据泄露**: 模拟敏感信息泄露
- **同意管理绕过**: 测试同意机制绕过

### 7. 金融安全测试
- **支付欺诈**: 模拟支付金额篡改
- **洗钱检测**: 测试可疑交易模式
- **加密货币攻击**: 模拟钱包攻击

### 8. 用户行为分析测试
- **异常访问时间**: 测试非工作时间访问
- **批量数据访问**: 模拟大量数据导出
- **会话劫持**: 测试会话劫持检测

### 9. 攻击链关联测试
- **多阶段攻击**: 模拟完整的攻击链
- **MITRE ATT&CK**: 测试攻击技术映射
- **横向移动**: 模拟网络横向移动

### 10. 自动化响应测试
- **自动阻断**: 测试IP自动阻断
- **自动隔离**: 模拟恶意软件隔离
- **告警升级**: 测试告警自动升级

## 📈 验证指标

测试框架从以下维度验证规则性能：

### 1. 规则覆盖率
- 检查每个类别的规则是否被正确触发
- 计算规则覆盖百分比
- 识别未被测试的规则

### 2. 威胁评分准确性
- 验证威胁评分的合理性
- 检查高威胁场景的评分
- 分析评分分布情况

### 3. 误报率控制
- 统计低威胁评分的成功匹配
- 计算误报率百分比
- 确保误报率在可接受范围内

### 4. 攻击模式识别
- 验证攻击模式的正确识别
- 检查模式覆盖的完整性
- 分析模式检测的准确性

### 5. 性能指标
- 计算整体测试成功率
- 分析各类别的性能差异
- 识别性能瓶颈

## 📄 报告解读

### HTML测试报告
- **统计概览**: 显示总体测试统计
- **类别详情**: 每个类别的详细测试结果
- **匹配规则**: 显示匹配的具体规则
- **威胁评分**: 展示每个测试的威胁评分

### 验证报告
- **总体评分**: 0-100分的综合评分
- **维度分析**: 各个验证维度的详细结果
- **改进建议**: 基于测试结果的优化建议

## 🔧 高级用法

### 自定义测试数据
```python
from tests.test_framework import TestFramework

# 创建测试框架
framework = TestFramework()

# 生成自定义测试数据
custom_logs = framework.generate_test_logs()

# 保存到指定文件
with open('custom_test_logs.json', 'w') as f:
    json.dump(custom_logs, f)
```

### 单独测试特定类别
```bash
# 只测试AI/ML异常检测规则
python3 tests/run_tests.py --category ai_ml_anomaly --run-tests
```

### 调整验证阈值
```python
from tests.result_validator import ResultValidator

# 创建验证器并调整阈值
validator = ResultValidator()
validator.expected_matches['ai_ml_anomaly'] = ['自定义规则名称']
```

## 🐛 故障排除

### 常见问题

1. **规则加载失败**
   ```
   错误: 规则目录不存在
   解决: 确保rules目录存在且包含YAML文件
   ```

2. **测试数据生成失败**
   ```
   错误: 无法生成测试日志
   解决: 检查Python环境和依赖包
   ```

3. **报告生成失败**
   ```
   错误: 无法生成HTML报告
   解决: 确保reports目录有写权限
   ```

### 调试模式
```bash
# 启用详细输出
./tests/run_all_tests.sh -v

# 查看测试日志
tail -f tests/test_framework.log
```

## 📝 扩展测试

### 添加新的测试类别
1. 在`test_framework.py`中添加新的生成方法
2. 更新`expected_matches`映射
3. 创建相应的测试场景

### 自定义验证逻辑
1. 继承`ResultValidator`类
2. 重写验证方法
3. 添加新的验证维度

## 🤝 贡献指南

欢迎为测试框架贡献代码：

1. Fork项目
2. 创建功能分支
3. 添加测试用例
4. 提交Pull Request

## 📞 支持

如需帮助，请：
1. 查看本文档
2. 检查测试日志
3. 提交Issue到项目仓库

---

**测试框架版本**: v1.0
**兼容规则引擎版本**: v3.1
**最后更新**: 2024-01-15