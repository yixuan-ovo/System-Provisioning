# System-Provisioning

系统配置与部署文档集合，包含服务器加固、VPN 组网、媒体中心配置等系统级配置教程。

## 📁 项目结构

```
System-Provisioning/
├── Kodi/                 # Kodi 媒体中心配置（连接 Jellyfin）
├── ps5_twittch/          # PS5 Twitch 推流到 B站配置
├── TailScale/            # Tailscale + 私有 DERP 高性能组网
├── Ubuntu_Server/         # Ubuntu 服务器标准加固与部署
├── WireGuard/            # WireGuard VPN 配置教程
└── win11_bug/            # Windows 11 修复注册表文件
```

## 🛠️ 组件介绍

### 1. Ubuntu Server 服务器加固

Ubuntu 服务器的安全加固和标准化部署流程。

**主要功能：**
- SSH 密钥认证配置
- 防火墙规则配置（iptables）
- Fail2Ban 入侵防护
- 内核级安全加固（sysctl）
- 账户权限强化

**相关文档：**
- [Ubuntu 服务器标准加固与部署](./Ubuntu_Server/ubuntu_服务器标准加固与部署.md)

**关键配置：**
- SSH 端口：38617（自定义）
- 禁用 root 登录，使用普通用户 + sudo
- 仅允许密钥认证，禁用密码登录
- iptables 防火墙策略
- Fail2Ban 自动封禁暴力破解

### 2. WireGuard VPN

基于 WireGuard 的 VPN 组网方案，适用于游戏联机、内网穿透等场景。

**主要功能：**
- 点对点 VPN 连接
- 虚拟局域网组网
- 低延迟游戏联机
- 内网穿透

**相关文档：**
- [WireGuard 配置教程](./WireGuard/配置wireguard.md)

**关键配置：**
- 默认端口：UDP 51820
- 虚拟网段：192.168.126.0/24（可自定义）
- MTU：1380（防止游戏大数据包分片）
- 支持多客户端连接
- 需要公网 IP 服务器

### 3. Tailscale + 私有 DERP

基于 Tailscale 的高性能组网方案，通过自建 DERP 中转节点实现低延迟直连。

**主要功能：**
- 零配置组网
- 私有 DERP 中转节点
- 自动打洞直连
- 跨平台支持

**相关文档：**
- [Tailscale DERP 部署教程](./TailScale/Tailscale_DERP_Setup.md)

**关键配置：**
- DERP 端口：TCP 31226、UDP 12263（STUN）
- 需要国内云服务器作为中转节点
- 同省同运营商延迟可低至 8ms
- 支持 UPnP 和 Full Cone NAT

### 4. PS5 Twitch 推流到 B站

通过 Docker 实现 PS5 Twitch 推流自动转发到 B站直播。

**主要功能：**
- PS5 Twitch 推流捕获
- 自动转发到 B站
- DNS 劫持实现透明转发
- Docker 容器化部署

**相关文档：**
- [PS5 Twitch 推流到 B站配置教程](./ps5_twittch/bao3playstation.md)

**关键组件：**
- `bao3/playstation` - RTMP 推流转发容器
- `jpillora/dnsmasq` - DNS 劫持服务
- 需要梯子环境
- 需要 B站推流地址和密钥

### 5. Kodi 媒体中心

Kodi 媒体中心配置，连接 Jellyfin 服务器。

**主要功能：**
- Jellyfin 插件安装
- 媒体库同步
- 远程媒体访问

**相关文档：**
- [Kodi 设置教程](./Kodi/kodi-settings.md)

**配置要点：**
- 安装 Jellyfin 插件
- 配置服务器连接
- 同步媒体库

### 6. Windows 11 Bug 修复

Windows 11 系统问题的注册表修复文件。

**包含修复：**
- DWM MPO 修复
- Overlay 最小 FPS 删除

**文件位置：**
- `win11_bug/reg/` - 注册表修复文件

## 🔧 快速开始

### 服务器环境部署

1. **Ubuntu 服务器加固**
   - 参考 [Ubuntu 服务器标准加固与部署](./Ubuntu_Server/ubuntu_服务器标准加固与部署.md)
   - 完成 SSH 密钥配置和防火墙设置

2. **选择 VPN 方案**
   - **WireGuard**：适合需要固定 IP 和低延迟的场景
   - **Tailscale**：适合零配置组网和跨平台使用

### 游戏联机方案

1. **WireGuard 直连**
   - 部署 WireGuard 服务器
   - 配置客户端连接
   - 设置防火墙规则

2. **Tailscale 组网**
   - 部署私有 DERP 节点
   - 配置 ACL 规则
   - 实现自动打洞直连

### 媒体中心配置

1. **Kodi + Jellyfin**
   - 安装 Kodi 客户端
   - 安装 Jellyfin 插件
   - 配置服务器连接

## 📝 配置要点

### 服务器安全

- **SSH 加固**：使用密钥认证，禁用密码登录
- **防火墙**：仅开放必要端口，使用 iptables 或 UFW
- **入侵防护**：配置 Fail2Ban 自动封禁
- **系统更新**：定期更新系统软件包

### VPN 组网

- **WireGuard**：需要公网 IP，配置 NAT 转发
- **Tailscale**：需要云服务器作为 DERP 节点
- **MTU 设置**：游戏场景建议 1380，避免分片
- **防火墙**：放行 VPN 端口和虚拟网卡流量

### 推流配置

- **DNS 劫持**：使用 dnsmasq 劫持推流域名
- **RTMP 转发**：使用 bao3/playstation 容器转发
- **网络配置**：PS5 DNS 设置为运行 Docker 的电脑 IP

## ⚠️ 注意事项

1. **VPN 配置**
   - WireGuard 需要公网 IP 服务器
   - Tailscale DERP 节点需要开放 STUN 端口
   - 游戏联机需要配置防火墙允许虚拟网卡流量

2. **推流配置**
   - Twitch 推流地址可能变化，需要定期更新 DNS 规则
   - 需要梯子环境才能拉取 Docker 镜像
   - B站推流地址和密钥需要从开播界面获取

## 🔄 更新日志

### 2025-08-11
- PS5 Twitch 推流：更新 DNS 测试方法

### 2025-05-20
- PS5 Twitch 推流：更新推流地址配置

### 2024-11-12
- PS5 Twitch 推流：增加完成截图

## 📚 相关资源

- [WireGuard 官方文档](https://www.wireguard.com/)
- [Tailscale 官方文档](https://tailscale.com/kb/)
- [Ubuntu 官方文档](https://ubuntu.com/server/docs)
- [Kodi 官方文档](https://kodi.wiki/)
- [Jellyfin 官方文档](https://jellyfin.org/docs/)

## 📄 许可证

本项目仅用于学习和研究目的，请遵守相关法律法规。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进本项目。

---

**最后更新**：2025-08-11
