# SSlogs 检测规则分类体系 v3.0

## 📊 分类统计概览

### 🔥 **核心安全威胁 (20个类别)**
| 类别 | 规则数量 | 威胁级别 | 覆盖范围 |
|------|----------|----------|----------|
| **injection** | 8个 | 🔴 Critical | SQL/NoSQL/LDAP/命令注入 |
| **xss** | 3个 | 🟠 High | 反射/存储/DOM型XSS |
| **rce** | 5个 | 🔴 Critical | 远程代码执行 |
| **ssrf** | 3个 | 🟠 High | 服务器请求伪造 |
| **api_security** | 4个 | 🟠 High | API/GraphQL/REST安全 |
| **business_logic** | 1个 | 🟠 High | 业务逻辑漏洞 |

### 🆕 **新兴威胁领域 (6个新类别)**
| 类别 | 规则数量 | 威胁级别 | 创新程度 |
|------|----------|----------|----------|
| **blockchain_security** | 1个 | 🔴 Critical | Web3/DeFi/NFT安全 |
| **mobile_security** | 1个 | 🟠 High | 移动应用安全 |
| **iot_security** | 1个 | 🔴 Critical | IoT/IIoT设备安全 |
| **apt_threat** | 1个 | 🔴 Critical | APT高级威胁 |
| **cloud_security** | 2个 | 🟠 High | 云原生安全 |
| **crypto_mining** | 4个 | 🟡 Medium | 挖矿恶意软件 |

### 🛡️ **基础安全防护 (18个类别)**
| 类别 | 规则数量 | 威胁级别 | 防护范围 |
|------|----------|----------|----------|
| **reconnaissance** | 6个 | 🟡 Medium | 信息收集和侦察 |
| **file_inclusion** | 2个 | 🟠 High | 文件包含漏洞 |
| **path_traversal** | 1个 | 🟠 High | 路径遍历攻击 |
| **webshell** | 1个 | 🔴 Critical | Web后门 |
| **brute_force** | 2个 | 🟡 Medium | 暴力破解 |
| **attack_tool** | 1个 | 🟡 Medium | 攻击工具检测 |

## 🎯 **按威胁级别分类**

### 🔴 **Critical (严重威胁)**
```yaml
- injection: SQL注入、NoSQL注入、命令注入等
- rce: 远程代码执行、Log4j漏洞等
- webshell: 后门上传和访问
- ssrf: 服务器端请求伪造
- blockchain_security: 区块链和DeFi攻击
- iot_security: IoT设备控制
- apt_threat: APT高级威胁
```

### 🟠 **High (高危威胁)**
```yaml
- xss: 跨站脚本攻击
- api_security: API安全威胁
- business_logic: 业务逻辑漏洞
- mobile_security: 移动应用安全
- cloud_security: 云原生安全
- file_inclusion: 文件包含攻击
- path_traversal: 路径遍历
```

### 🟡 **Medium (中危威胁)**
```yaml
- reconnaissance: 信息收集
- brute_force: 暴力破解
- crypto_mining: 挖矿恶意软件
- attack_tool: 攻击工具检测
- misconfiguration: 配置错误
- information_disclosure: 信息泄露
```

## 🏗️ **按攻击技术分类**

### 💉 **注入攻击类**
- SQL注入 (`sql_injection.yaml`)
- NoSQL注入 (`nosql_injection.yaml`)
- LDAP注入 (`ldap_injection.yaml`)
- 命令注入 (`command_injection.yaml`)
- 模板注入 (`ssti_detection.yaml`)
- HTTP参数污染 (`hpp_attack.yaml`)

### 🎭 **客户端攻击类**
- XSS攻击 (`xss_attack.yaml`)
- CSRF攻击 (`csrf_attack.yaml`)
- 点击劫持 (集成在xss规则中)
- 重定向攻击 (`unvalidated_redirect.yaml`)

### 🔧 **服务端攻击类**
- 文件包含 (`file_inclusion.yaml`)
- 路径遍历 (`path_traversal.yaml`)
- 文件上传 (`file_upload_attack.yaml`)
- RCE攻击 (`rce_detection.yaml`)
- WebShell (`webshell_access.yaml`)

### 🔍 **信息收集类**
- 扫描器检测 (`scanner_detection.yaml`)
- Nmap扫描 (`nmap_scan.yaml`)
- 暴力破解 (`brute_force.yaml`)
- 目录爆破 (`directory_brute_force.yaml`)
- 商业扫描器 (`commercial_scanners.yaml`)

## 🌐 **按平台和环境分类**

### 📱 **移动平台**
- **移动应用安全** (`mobile_app_security.yaml`)
  - API安全
  - 证书绕过
  - 数据泄露
  - 支付攻击

### ☁️ **云环境**
- **云原生安全** (`cloud_native_threats.yaml`)
  - Kubernetes安全
  - 容器逃逸
  - 云元数据攻击
- **云配置错误** (`cloud_metadata_access.yaml`)

### 🔗 **区块链平台**
- **Web3安全** (`blockchain_web3_security.yaml`)
  - 智能合约漏洞
  - DeFi攻击
  - NFT安全
  - MEV攻击

### 🌐 **物联网平台**
- **IoT安全** (`iot_security.yaml`)
  - 设备默认凭据
  - 固件攻击
  - 协议安全
  - 僵尸网络

## 🎯 **按业务场景分类**

### 💰 **电商和支付**
- 支付绕过
- 价格篡改
- 优惠券滥用
- 积分刷取

### 🗳️ **社交和内容**
- 投票系统攻击
- 内容篡改
- 账号劫持

### 🎮 **游戏和娱乐**
- 游戏作弊
- 虚拟货币滥用
- 排名篡改

### 🏥 **医疗健康**
- 医疗设备安全
- 隐私数据保护
- 医疗系统攻击

## 📈 **优化建议和发展方向**

### 🔥 **高优先级扩展**
1. **机器学习检测** - 异常行为模式识别
2. **威胁情报集成** - IOC自动匹配
3. **攻击链分析** - 多步骤攻击关联
4. **行为分析** - 用户和实体行为(UEBA)

### 🎯 **中优先级扩展**
1. **行业特定规则** - 金融、医疗、制造业
2. **区域化威胁** - 地区性攻击模式
3. **零信任架构** - 身份和访问控制
4. **隐私保护** - GDPR/HIPAA合规检测

### 🚀 **长期发展方向**
1. **AI驱动规则** - 自动规则生成和优化
2. **社区规则库** - 开源贡献和共享
3. **实时更新** - 动态威胁情报同步
4. **自定义规则** - 可视化规则编辑器

---

**当前总规则数: 60+个 | 覆盖领域: 25+个 | 威胁类型: 100+种**

通过这样的分类体系，SSlogs能够提供全方位、多层次的安全威胁检测覆盖。🛡️