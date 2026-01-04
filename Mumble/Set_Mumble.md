# Mumble 服务器设置指南

## 1. 安装服务端

```bash
sudo apt update
sudo apt install mumble-server
```

## 2. 基础配置

安装完成后，运行配置向导：

```bash
sudo dpkg-reconfigure mumble-server
```

配置选项说明：

- **Autostart**: 选择 `Yes`（随系统启动）
- **High Priority**: 选择 `Yes`（保证语音流畅）
- **SuperUser password**: 设置一个密码（这是管理服务器的最高权限密码，请妥善保管）

## 3. 防火墙配置

Mumble 默认使用 **64738** 端口，需要同时开放 TCP 和 UDP 协议。

### 使用 UFW 配置

```bash
# 开放 TCP 端口（控制连接）
sudo ufw allow 64738/tcp

# 开放 UDP 端口（语音数据，必须开放，否则无法听到声音）
sudo ufw allow 64738/udp
```

### 云服务器安全组配置

如果使用云服务器（如腾讯云/阿里云），还需要在控制台的安全组/防火墙中添加相应规则：

- **协议**: TCP，端口: 64738
- **协议**: UDP，端口: 64738

> **注意**: 语音数据走 UDP，如果不开这个端口，连接后无法听到声音。

## 4. 进阶优化配置

编辑配置文件进行高级设置：

```bash
sudo nano /etc/mumble-server.ini
```

### 常用配置项说明

| 配置项 | 说明 | 推荐值 |
|--------|------|--------|
| `port` | 监听端口 | `64738`（默认） |
| `host` | 监听 IP 地址 | 留空表示监听所有 IP（包括公网 IP 和 Tailscale IP） |
| `serverpassword` | 服务器密码 | 如需私密服务器，在此设置密码 |
| `bandwidth` | 单用户最大码率 | `72000`（约 70kbps），人多时可降至 `50000` |
| `users` | 最大同时在线人数 | `100`（根据服务器性能调整） |
| `welcometext` | 欢迎消息 | 自定义 HTML 格式文本 |
| `imagemessagelength` | 单张图片大小限制 | `131072`（128KB），3M 带宽建议调小 |
| `logdays` | 日志保留天数 | `31`（一个月） |

### 配置示例

```ini
port=64738
host=
serverpassword=
bandwidth=72000
users=100
welcometext="<br /> 加入频道视为 <b>自愿</b> <br />穿越神圣泰拉!<br />"
imagemessagelength=131072
logdays=31
```

修改配置后，重启服务使配置生效：

```bash
sudo systemctl restart mumble-server
```

## 5. 获取 SuperUser 权限

在 Mumble 客户端连接后，有两种方式获取管理员权限：

1. **右键根频道** → 选择"注册"
2. **服务器菜单** → "管理员" → 输入之前设置的 SuperUser 密码

获取权限后，即可在图形化界面中：
- 创建和管理频道
- 拖拽用户到不同频道
- 管理用户权限

## 6. 连接方式

### 方案 A：通过公网 IP 连接（最方便）

适用于所有用户，需要开放公网端口。

**连接步骤**：
1. 在 Mumble 客户端输入服务器的公网 IP 地址
2. 端口使用默认的 `64738`（如果修改了配置则使用对应端口）
3. 如果设置了 `serverpassword`，需要输入服务器密码

**优点**：
- 配置简单，无需额外软件
- 适合临时使用

**缺点**：
- 需要开放公网端口，存在安全风险
- 受公网带宽限制（如 3M 带宽）

### 方案 B：通过 Tailscale 连接（推荐，最稳定）

适用于所有用户都安装了 Tailscale 的场景。

**前提条件**：
- 服务器已安装并配置 Tailscale
- 所有用户都已加入同一个 Tailscale 网络

**连接步骤**：
1. 获取服务器的 Tailscale IP 地址（通常是 `100.x.x.x`）
2. 在 Mumble 客户端输入 Tailscale IP 地址
3. 端口使用默认的 `64738`

**优点**：
- **低延迟**: Tailscale 会尝试点对点（P2P）连接，延迟更低
- **更稳定**: 不依赖公网质量
- **更安全**: 可以关闭公网端口，只允许内网访问，防止恶意扫描
- **不受带宽限制**: 如果用户在同一个虚拟内网，不受 3M 公网带宽限制

**安全建议**：
如果使用 Tailscale，建议关闭云服务器上的 64738 公网端口，只允许 Tailscale 内网访问。

---

## 常见问题

### 服务管理命令

```bash
# 启动服务
sudo systemctl start mumble-server

# 停止服务
sudo systemctl stop mumble-server

# 重启服务
sudo systemctl restart mumble-server

# 查看服务状态
sudo systemctl status mumble-server

# 查看日志
sudo journalctl -u mumble-server -f
```

### 无法听到声音

- 检查 UDP 端口 64738 是否已开放
- 检查防火墙规则是否正确
- 检查客户端音频设置

### 连接延迟高

- 考虑使用 Tailscale 方案
- 降低 `bandwidth` 配置值
- 检查服务器网络质量
