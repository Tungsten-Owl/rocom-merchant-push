# 洛克王国远行商人商品定时邮件推送

自动获取洛克王国远行商人商品数据，并在每个时段开始时通过邮件通知收件人。

## 功能特性

- **定时推送**：每天4个时段自动发送商品信息邮件
- **智能重试**：API未返回商品数据时，每分钟自动重试（最多30次）
- **延迟触发**：时段开始后延迟2分钟再请求API，确保数据已更新
- **配置校验**：启动时检查配置文件完整性和必要性
- **HTML邮件**：包含商品图片、价格、限购信息的美观邮件模板
- **多收件人**：支持同时发送给多个邮箱地址

## 时段说明

远行商人商品按时段轮换，每天共4个时段：

| 时段 | 时间范围 | 邮件发送时间 |
|------|----------|--------------|
| 上午场 | 08:00 - 12:00 | 08:02 |
| 下午场 | 12:00 - 16:00 | 12:02 |
| 傍晚场 | 16:00 - 20:00 | 16:02 |
| 夜间场 | 20:00 - 24:00 | 20:02 |

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置

复制示例配置文件并填写你的邮箱信息：

```bash
copy config.example.ini config.ini
```

编辑 `config.ini`，填写以下必要配置：

```ini
[smtp]
# SMTP 服务器地址（QQ邮箱为 smtp.qq.com）
host = smtp.qq.com

# SMTP 端口（SSL通常为465，STARTTLS通常为587）
port = 465

# 是否使用 SSL
use_ssl = true

# 发件人邮箱
sender = your_email@qq.com

# 发件人邮箱授权码（非登录密码，需在邮箱设置中生成）
password = your_authorization_code

# 收件人邮箱（多个用逗号分隔）
recipients = recipient1@example.com, recipient2@example.com

[api]
# API 地址（使用默认值即可）
url = https://rocom-api.ovofish.com/api/shop

# API Key（使用公开免费的Key即可）
key = sk-f2141ba4be3a9832106d2dc4042454666e354414d3ed0ce9
```

### 3. 运行

```bash
python main.py
```

程序启动后会：
1. 检查配置文件完整性
2. 显示当前配置信息
3. 注册定时任务
4. 如果当前处于营业时段（且已过2分钟缓冲），立即执行一次推送
5. 持续运行，按 `Ctrl+C` 退出

## API说明

本项目使用洛克王国远行商人商品API：

- **接口地址**：`https://rocom-api.ovofish.com/api/shop`
- **认证方式**：Header中携带 `X-API-Key`
- **公开Key**：`sk-f2141ba4be3a9832106d2dc4042454666e354414d3ed0ce9`（免费使用）

### API响应状态

| 状态 | 说明 | 程序行为 |
|------|------|----------|
| `success` | 成功获取商品数据 | 发送邮件 |
| `loading` | 前置引擎工作中（时段前2分钟） | 等待1分钟后重试 |
| `closed` | 未营业（00:00-08:00） | 等待1分钟后重试 |
| `error` | 获取商品信息失败 | 等待1分钟后重试 |
| 空商品列表 | 无商品数据 | 等待1分钟后重试 |

## 邮件效果

邮件包含以下信息：
- 商品图片
- 商品名称
- 价格（洛克贝）
- 限购数量
- 下架时间

示例邮件主题：`洛克王国远行商人 - 下午场 商品提醒`

## 配置说明

### 邮箱配置

| 配置项 | 说明 | 示例 |
|--------|------|------|
| `host` | SMTP服务器地址 | `smtp.qq.com` |
| `port` | SMTP端口 | `465`（SSL）或 `587`（STARTTLS） |
| `use_ssl` | 是否使用SSL | `true` |
| `sender` | 发件人邮箱 | `your_email@qq.com` |
| `password` | 邮箱授权码 | `xxxxxxxxxxxx` |
| `recipients` | 收件人邮箱（逗号分隔） | `a@example.com, b@example.com` |

### 获取QQ邮箱授权码

1. 登录QQ邮箱
2. 进入「设置」→「账户」
3. 找到「POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务」
4. 开启「IMAP/SMTP服务」
5. 生成授权码（16位字符串）

## 错误处理

### 配置文件缺失
```
[ERROR] 配置文件 config.ini 不存在
[HINT]  请复制 config.example.ini 为 config.ini 并填写配置
```

### 配置项缺失
```
[ERROR] 配置文件缺少以下必要配置项:
  - [smtp] password
  - [api] url
[HINT]  请检查 config.ini 并补充缺失的配置
```

### API请求失败
程序会自动重试，每分钟尝试一次，最多重试30次：
```
[INFO] 第 1 次尝试: status=loading, 商品数=0，1分钟后重试...
```

## 日志输出

程序运行时会输出详细日志：
- `[时间] 执行任务: 下午场` - 任务开始
- `[INFO] 第 1 次尝试: status=success, 商品数=3` - API请求结果
- `[OK] 邮件已发送 -> recipient@example.com` - 邮件发送成功
- `[ERROR] 邮件发送失败: ...` - 邮件发送失败

## 注意事项

1. **邮箱授权码**：不是邮箱登录密码，需要在邮箱设置中单独生成
2. **网络环境**：确保能访问 `rocom-api.ovofish.com`
3. **程序持续运行**：需要保持程序运行才能按时发送邮件
4. **时区设置**：程序使用系统时区（Asia/Shanghai）
5. **安全提示**：`config.ini` 包含敏感信息，已在 `.gitignore` 中忽略

## 依赖

- Python 3.6+
- requests - HTTP请求库
- schedule - 定时任务库

## 许可证

MIT License
