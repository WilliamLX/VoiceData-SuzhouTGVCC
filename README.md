# 腾讯云COS语音数据处理工具

这是一个用于处理腾讯云COS中语音数据的Python工具集，支持对象列表获取、批量下载、增量同步等功能。

## 功能特性

- 🔍 **对象列表获取**: 支持前缀筛选、分页获取COS对象列表
- ⬇️ **批量下载**: 多线程并发下载，支持断点续传
- 📊 **进度显示**: 实时显示下载进度和统计信息
- 🔒 **配置管理**: 支持JSON配置文件，保护敏感信息
- 📝 **详细日志**: 完整的操作日志记录
- 🚀 **性能优化**: 智能重试、并发控制、文件过滤

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone <repository-url>
cd VoiceData-SuzhouTGVCC

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置设置

复制配置文件模板并填写您的COS信息：

```bash
cp config_example.json config.json
```

编辑 `config.json`：

```json
{
  "cos_config": {
    "secret_id": "YOUR_SECRET_ID_HERE",
    "secret_key": "YOUR_SECRET_KEY_HERE",
    "region": "ap-beijing",
    "bucket_name": "your-bucket-name"
  },
  "options": {
    "prefix": "Record/",
    "output_file": "cos_objects.json",
    "download_dir": "/Users/server1/Library/Mobile Documents/com~apple~CloudDocs/Data",
    "max_keys_per_request": 1000
  }
}
```

### 3. 基本使用

#### 获取对象列表
```bash
# 使用配置文件
python cos_with_config.py

# 指定前缀
python cos_with_config.py --prefix "Record/2024/"

# 自定义输出文件
python cos_with_config.py --output objects_list.json
```

#### 批量下载
```bash
# 基础下载
python cos_enhanced_downloader.py

# 高级下载（多线程、文件过滤）
python cos_enhanced_downloader.py \
    --workers 8 \
    --extensions .mp3 .wav \
    --min-size 1000000 \
    --output-dir voice_data
```

## 工具说明

### cos_with_config.py
配置文件版本的COS对象获取工具，支持从JSON配置文件读取配置信息。

**特性：**
- 支持配置文件管理
- 命令行参数覆盖配置
- 对象信息保存为JSON
- 大小统计和显示

### cos_enhanced_downloader.py
增强版下载器，支持多线程并发下载、断点续传、进度显示等功能。

**特性：**
- 多线程并发下载
- 断点续传（MD5校验）
- tqdm进度条显示
- 文件过滤（扩展名、大小）
- 智能重试机制
- 详细日志记录
- 下载报告生成

### cos_simple.py
简单版本的COS对象获取工具，支持命令行参数直接指定配置。

**特性：**
- 命令行参数配置
- 简单易用
- 快速测试

## 配置说明

### COS配置
- `secret_id`: 腾讯云SecretId
- `secret_key`: 腾讯云SecretKey
- `region`: COS地域（如：ap-beijing）
- `bucket_name`: 存储桶名称

### 选项配置
- `prefix`: 对象前缀筛选
- `output_file`: 输出JSON文件路径
- `download_dir`: 下载目录
- `max_keys_per_request`: 每次请求的最大对象数

## 命令行参数

### cos_with_config.py
```bash
python cos_with_config.py [选项]

选项:
  --config CONFIG     配置文件路径 (默认: config.json)
  --prefix PREFIX     对象前缀筛选
  --output OUTPUT     输出JSON文件路径
```

### cos_enhanced_downloader.py
```bash
python cos_enhanced_downloader.py [选项]

选项:
  --config CONFIG         配置文件路径
  --workers WORKERS       并发下载数 (默认: 5)
  --retry RETRY          重试次数 (默认: 3)
  --prefix PREFIX        对象前缀筛选
  --extensions EXTENSIONS 文件扩展名过滤
  --min-size MIN_SIZE    最小文件大小（字节）
  --max-size MAX_SIZE    最大文件大小（字节）
  --output-dir OUTPUT_DIR 输出目录
  --no-progress          禁用进度条
  --no-log-file          禁用日志文件
```

## 日志和报告

### 日志文件
- 位置：`logs/download_YYYYMMDD_HHMMSS.log`
- 内容：详细的操作日志，包括成功/失败信息

### 下载报告
- 位置：`download_report_YYYYMMDD_HHMMSS.json`
- 内容：下载统计信息、配置参数、时间戳

## 安全注意事项

1. **配置文件安全**
   - 不要将包含真实密钥的配置文件提交到版本控制
   - 使用环境变量或加密存储敏感信息
   - 定期更换密钥

2. **网络安全**
   - 使用HTTPS连接
   - 设置适当的超时时间
   - 监控异常访问

3. **数据安全**
   - 定期备份重要数据
   - 验证下载文件的完整性
   - 保护本地存储的数据

## 故障排除

### 常见问题

1. **配置文件错误**
   ```
   错误: 配置文件不存在或格式错误
   解决: 检查config.json文件是否存在且格式正确
   ```

2. **认证失败**
   ```
   错误: 认证失败
   解决: 检查SecretId和SecretKey是否正确
   ```

3. **网络连接问题**
   ```
   错误: 网络连接超时
   解决: 检查网络连接，增加重试次数
   ```

4. **权限不足**
   ```
   错误: 访问被拒绝
   解决: 检查COS权限设置
   ```

### 调试模式

启用详细日志：
```bash
python cos_enhanced_downloader.py --verbose
```

## 开发计划

- [x] 基础对象列表获取
- [x] 配置文件支持
- [x] 多线程下载
- [x] 断点续传
- [x] 进度显示
- [x] 日志记录
- [ ] 增量同步
- [ ] 安全性增强
- [ ] 对象操作扩展

## 贡献指南

欢迎提交Issue和Pull Request来改进这个项目。

## 许可证

本项目采用MIT许可证。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交GitHub Issue
- 发送邮件至项目维护者

---

**注意**: 请确保您有足够的COS权限来执行相关操作。 