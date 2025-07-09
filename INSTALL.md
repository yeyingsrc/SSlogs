# 生产环境安装指南

## 基础安装
```bash
# 克隆项目
git clone <repository-url>
cd SSlogs

# 安装基础依赖
pip install -r requirements.txt
```

## 可选依赖安装

### 开发环境完整安装
```bash
# 安装开发依赖（包含测试、代码质量工具等）
pip install -r requirements-dev.txt
```

### 最小化安装
如果只需要基本功能，可以手动安装最少依赖：
```bash
pip install PyYAML requests geoip2 patool
```

## 依赖说明

### 必需依赖
- **PyYAML**: 配置文件和规则文件解析
- **requests**: AI API调用和HTTP请求
- **geoip2**: IP地理位置查询
- **patool**: 压缩文件处理

### 功能依赖
- **Jinja2**: HTML报告模板渲染（如果不生成HTML报告可以不安装）
- **charset-normalizer**: 字符编码处理（提升文本解析准确性）

### 系统要求
- Python 3.8+
- 可用内存: 建议1GB+（处理大文件时）
- 磁盘空间: 根据日志文件大小而定

## 故障排除

### 安装问题
```bash
# 如果遇到权限问题
pip install --user -r requirements.txt

# 如果遇到网络问题，使用镜像源
pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

### 依赖冲突
```bash
# 使用虚拟环境避免冲突
python -m venv sslogs_env
source sslogs_env/bin/activate  # Linux/Mac
# 或
sslogs_env\Scripts\activate     # Windows
pip install -r requirements.txt
```