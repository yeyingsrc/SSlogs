# SSlogs 安全审计报告

**审计时间**：2026-05-28  
**审计范围**：全仓库代码 + 配置 + 规则 + 部署  
**仓库**：https://github.com/wooluo/SSlogs  
**代码规模**：~40,000行 / 73条检测规则  

---

## 综合评分：6.2 / 10

作为安全日志分析工具，检测规则引擎做得不错（73条规则、置信度分级），但自身安全性存在明显短板。一个安全工具如果自己都不安全，说服力大打折扣。

---

## 🔴 Critical（必须立即修复）

### C1. config.yaml 硬编码 API Key

**文件**：`config.yaml:57`

```yaml
deepseek:
  api_key: demo_key_for_testing
```

`demo_key_for_testing`虽然是占位符，但代码中`AIAnalyzer._get_secure_api_key()`会直接使用它发请求。如果用户忘了改，就用这个假key打到siliconflow.cn。更危险的是，有人会把真实key直接写在这里然后push到GitHub。

**修复**：
- `config.yaml`中改为`api_key: ""`，空值时拒绝初始化
- `_get_secure_api_key()`空key时抛`AIServiceError`而不是返回空字符串
- README中强调必须通过环境变量`SSLOGS_AI_API_KEY`传入

### C2. tarfile 路径遍历（Zip Slip）

**文件**：`main.py:167-171`

```python
with tarfile.open(file, 'r:gz') as tar:
    for member in tar.getmembers():
        if member.isfile() and member.name.lower().endswith('.log'):
            with tar.extractfile(member) as f:
```

遍历tar成员时没有检查`member.name`是否包含`../`路径。攻击者可以构造一个恶意tar包，其中包含`../../.bashrc`之类的路径。虽然这里用的是`extractfile()`（只读不写），没有文件写出风险，但`tar.getmembers()`本身也可能触发[CVE-2007-4559](https://docs.python.org/3/library/tarfile.html#tarfile.tarfile.getmembers)相关的symlink问题。

**修复**：
```python
import tarfile

def _safe_tar_members(tar):
    for member in tar:
        if member.name.startswith(('/', '..')):
            raise ValueError(f"恶意tar路径: {member.name}")
        if member.issym() or member.islnk():
            continue  # 跳过符号链接
        yield member

# 使用
with tarfile.open(file, 'r:gz') as tar:
    for member in _safe_tar_members(tar):
        if member.isfile() and member.name.lower().endswith('.log'):
            ...
```

### C3. pickle 不安全反序列化

**文件**：`core/advanced_cache.py:246,274,376,385`

```python
value = pickle.load(f)      # L246
pickle.dump(value, f)       # L274
return pickle.loads(data)   # L376
data = pickle.dumps(value)  # L385
```

pickle反序列化可以执行任意代码。如果缓存文件被篡改（或Redis被入侵），攻击者可以RCE。

**修复**：
- 改用`json`序列化（数据都是dict/list/str，不需要pickle）
- 如果必须用二进制序列化，用`msgpack`代替

### C4. Web API 无认证 + CORS全开 + 0.0.0.0监听

**文件**：`web/model_api.py:24,1705-1710`

```python
CORS(app)  # 无参数 = 允许所有Origin
app.run(host="0.0.0.0", port=8080, debug=debug, threaded=True)
```

- 无认证：任何人都可以调用API管理模型、读取配置
- CORS全开：恶意网站可以跨域调用你的API
- 0.0.0.0：公网暴露
- `debug=True`时暴露 Werkzeug debugger（可RCE）

**修复**：
```python
CORS(app, origins=["http://localhost:3000"])  # 限制Origin
app.run(host="127.0.0.1", port=8080, debug=False)
# 添加 API Key 认证中间件
@app.before_request
def check_auth():
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    if not validate_session_token(token):
        return jsonify({'error': 'Unauthorized'}), 401
```

---

## 🟠 High（尽快修复）

### H1. Redis默认弱密码

**文件**：`docker-compose.yml:130`

```yaml
command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD:-sslogs123}
```

`sslogs123`是弱密码，且Redis默认没有bind限制。如果部署到公网，Redis裸奔+弱密码=被挖矿。

**修复**：
- 去掉默认密码，`REDIS_PASSWORD`为空时不启动Redis
- 添加`--bind 127.0.0.1`
- 或者Redis不暴露端口，只走Docker内部网络

### H2. PostgreSQL默认弱密码

**文件**：`docker-compose.yml:146`

```yaml
POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-sslogs123}
```

同上。且PostgreSQL端口5432暴露到宿主机。

**修复**：
- 去掉端口映射`ports: - "5432:5432"`（服务间通过Docker网络通信）
- 密码必须通过`.env`传入，不要有默认值

### H3. Web API大量innerHTML使用

**文件**：`web/model_api.py`（20+处）

大量使用`innerHTML`插入服务端返回的内容，存在XSS风险。虽然这里是管理界面不是公网应用，但如果攻击者能控制AI模型的返回内容（如Ollama的响应被污染），就可能注入恶意JS。

**修复**：
- 使用`textContent`代替`innerHTML`
- 或者对插入内容做HTML escape

### H4. 会话Token存储在内存

**文件**：`core/security_validator.py:531-554`

```python
self.session_tokens: Dict[str, Dict[str, Any]] = {}
```

- 重启丢失所有会话
- 无会话上限，理论上可以OOM
- 单进程模式，多Worker不共享

**修复**：
- 用Redis存储会话
- 添加最大会话数限制
- 定期清理过期会话（已有`cleanup_expired_sessions`但没看到定时调用）

### H5. Docker healthcheck 无意义

**文件**：`docker-compose.yml:68`

```yaml
healthcheck:
  test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
```

这个healthcheck永远成功，等于没有。应该检查应用是否真正健康。

**修复**：
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
```

### H6. 输入验证器的命令注入误报

**文件**：`core/security_validator.py:139-146`

```python
SecurityRule(
    name="Command Injection - Unix",
    pattern=re.compile(r'(?i)(;|\||&|`|\$\(|\$\{)'),
```

分号、管道符、&、$() 是正常日志内容（URL参数、User-Agent等）。这个规则会把大量正常日志条目标记为"命令注入"。对安全日志分析工具来说，自身把正常流量标记为攻击 = 误报率爆炸。

**修复**：
- 这个验证器应用于用户输入（如CLI参数），不应用于日志内容分析
- 或者提高验证级别阈值，这些规则只在STRICT/PARANOID模式下启用

---

## 🟡 Medium（建议修复）

### M1. 日志配置硬编码Mac路径

**文件**：`config.yaml:97`

```yaml
geoip_db_path: /Users/wooluo/DEV/SSlogs/config/GeoLite2-Country.mmdb
```

这是你MacBook上的路径，Linux部署必然失败。

**修复**：改为相对路径`config/GeoLite2-Country.mmdb`

### M2. config.yaml中`rules`字段重复定义

**文件**：`config.yaml:30-31` 和 `config.yaml:105-107`

```yaml
rules:
  default_severity: medium    # L30
...
rules:
  path: rules/                # L105
  auto_reload: true
```

YAML中同名key会被覆盖。第一个`rules`定义被第二个覆盖了，`default_severity`不生效。

**修复**：合并为一个`rules`字段。

### M3. requirements.txt版本过旧

```
requests==2.31.0      # 当前 2.32.x，有安全修复
urllib3==1.26.18      # 1.x已停止维护，应升级到2.x
Jinja2==3.1.2         # 当前3.1.4+，有安全修复
```

**修复**：用`pip-audit`或`safety audit`扫描依赖漏洞，升级到最新稳定版。

### M4. `_load_config`方法定义了两次

**文件**：`main.py:99-127` 和 `main.py:46`（通过ConfigManager）

`_load_config`在`main.py`中定义了但实际不调用（用的是`ConfigManager.load_config()`）。死代码造成混淆。

**修复**：删除`_load_config`方法。

### M5. tarfile处理只看.log后缀

**文件**：`main.py:169,177,186`

```python
if member.name.lower().endswith('.log'):
```

很多日志文件不以`.log`结尾（如`access.log.1`、`error_log`、`nginx_access_20260528.gz`、无后缀的日志）。建议增加配置项或更宽松的过滤。

### M6. 规则文件缺少CVE/CWE关联

73条规则中，只有少数（如`sql_injection.yaml`）标注了CWE和OWASP。大部分规则缺少这些关键字段，不利于合规报告生成。

---

## 🟢 Low（锦上添花）

### L1. 过多README和文档文件

仓库中有12个README/IMPROVEMENT/REPORT类的markdown文件，散落在根目录。用户不知道看哪个。

**建议**：合并为一个主`README.md`，其余移到`docs/`目录。

### L2. `rules_optimized/`目录与`rules/`并存

两套规则目录让人困惑。如果`rules_optimized`是替代品，应该直接替换；如果是实验性的，应该在README中说明。

### L3. 测试结果文件提交到Git

**文件**：`tests/results/test_results_20251016_*.json`

这些是2025年10月的测试结果，不应该提交到代码仓库。

**修复**：加入`.gitignore`

### L4. 命令注入规则过于敏感

`rules/command_injection.yaml`中的模式会匹配大量正常URL（如包含`|`的base64参数、含`;`的Cookie值）。建议提高置信度阈值。

### L5. `patoolib`依赖过重

只为了支持RAR就引入了`patoolib`，它依赖系统级的`unrar`/`p7zip`等工具。不如明确文档说明RAR支持需要额外安装。

---

## 📊 规则引擎评估

| 维度 | 评分 | 说明 |
|------|------|------|
| 覆盖面 | 8/10 | 73条规则覆盖OWASP Top10 + 挖矿 + APT + 云原生 |
| 误报控制 | 6/10 | 置信度分级思路好，但命令注入/XSS规则过于敏感 |
| 规则质量 | 7/10 | sql_injection.yaml写得很专业，但很多4行规则太单薄 |
| 可维护性 | 5/10 | rules/和rules_optimized/并存，CATEGORIES.md未更新 |
| 扩展性 | 8/10 | YAML格式易于添加新规则，rule_engine支持动态加载 |

**亮点**：sql_injection.yaml的置信度分级设计值得肯定。

**建议补充的规则**：
- Log4Shell变体（当前只有log4j_vulnerability，缺少后续CVE）
- Spring4Shell
- HTTP/2走私
- WebSocket滥用
- API速率限制异常检测

---

## 🔧 架构建议

1. **分离Web API**：`web/model_api.py`有1716行，其中1500+行是HTML模板。应该拆分为Flask Blueprint + 独立模板文件
2. **配置统一管理**：当前有`config.yaml` + `config/ai_config.yaml` + `emergency_config.json` + `emergency_collector_config.json`，建议统一到一个入口
3. **日志级别可调**：生产环境应该能动态调整日志级别，不需要重启
4. **添加CVE数据库**：可以集成NVD/CNVD的API，对匹配到的攻击模式自动关联已知CVE

---

*审计完成。以上问题按优先级排列，Critical级别建议本周内修复。*
