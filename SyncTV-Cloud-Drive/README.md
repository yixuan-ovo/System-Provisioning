# SyncTV + 服务器监控服务部署指南

## ⚠️ 重要提示

**本 `docker-compose.yml` 基于 Tailscale 内网 IP 进行部署。**

- 如果使用 Tailscale：保持当前配置，确保 `ports` 下的 IP 地址与你的 Tailscale IP 一致
- 如果直接部署（不使用 Tailscale）：需要删除 `docker-compose.yml` 中 `ports` 下的 IP 地址，改为仅端口映射

例如：
```yaml
# Tailscale 部署（当前配置）
ports:
  - "100.96.63.22:5244:5244"

# 直接部署（需要修改为）
ports:
  - "5244:5244"
```

---

## 1. 安装 Docker

### 安装 Docker Engine

```bash
curl -fsSL https://get.docker.com | bash
```

### 安装 Docker Compose 插件

```bash
sudo apt update && sudo apt install docker-compose-plugin -y
```

### 设置 Docker 开机自启

```bash
sudo systemctl enable docker
sudo systemctl start docker
```

验证安装：

```bash
docker --version
docker compose version
```

---

## 2. 准备部署环境

### 创建数据目录

`docker-compose.yml` 文件和 `data` 文件夹需要在同一目录下。

```bash
# 创建数据目录
mkdir -p data/uptime-kuma
mkdir -p data/filecodebox
mkdir -p data/alist
mkdir -p data/sun-panel/conf
mkdir -p data/sun-panel/uploads
mkdir -p data/sun-panel/database
mkdir -p synctv
```

### 修改配置（如需要）

如果使用 Tailscale，请确保 `docker-compose.yml` 中的 IP 地址（`100.96.63.22`）与你的 Tailscale IP 一致。

查看 Tailscale IP：

```bash
tailscale ip
```

---

## 3. 启动服务

### 方式一：使用 Docker Compose（推荐）

```bash
docker compose up -d
```

### 方式二：手动拉取镜像后启动

如果需要预先拉取镜像：

```bash
# 拉取所有镜像
docker compose pull

# 启动服务
docker compose up -d
```

### 查看服务状态

```bash
# 查看运行中的容器
docker compose ps

# 查看日志
docker compose logs -f

# 查看特定服务日志
docker compose logs -f synctv
```

---

## 4. 服务说明

部署完成后，以下服务将可用：

| 服务 | 端口 | 说明 | 访问地址 |
|------|------|------|----------|
| **Uptime Kuma** | 12861 | 服务监控 | `http://[IP]:12861` |
| **FileCodeBox** | 26861 | 文件分享 | `http://[IP]:26861` |
| **Excalidraw** | 23971 | 在线绘图 | `http://[IP]:23971` |
| **Sun-Panel** | 80 | 管理面板 | `http://[IP]` |
| **Glances** | 61208 | 系统监控 | `http://[IP]:61208` |
| **SyncTV** | 23862 | 同步播放 | `http://[IP]:23862` |
| **Alist** | 5244 | 文件管理 | `http://[IP]:5244` |

> **注意**：
> - `[IP]` 为你的 Tailscale IP 或服务器公网 IP
> - Uptime Kuma 和 Glances 使用 host 网络模式，端口由程序决定
> - 建议通过防火墙限制端口访问，仅允许 Tailscale 网络访问

---

## 5. 配置监控项

服务启动后，在 **Uptime Kuma**（`http://[IP]:12861`）中配置其余监控项：

1. 访问 Uptime Kuma 管理界面
2. 添加需要监控的服务和端点
3. 设置告警通知（可选）

---

## 6. 本地 Alist 服务配置

### 安装本地 Alist（Windows）

如果需要在本地挂载 Alist 服务，将本地影音文件交给 SyncTV 播放：

```bash
# 使用 nssm 安装 Alist 为 Windows 服务
.\nssm install alist
```

### 配置本地媒体文件夹

1. 访问本地 Alist 管理界面：`http://localhost:5244`
2. 登录管理后台（首次访问会显示初始密码）
3. 添加存储，选择本地路径
4. 配置媒体文件夹路径（例如：`D:\Movies`）

### 在 SyncTV 中添加本地资源

1. **进入 SyncTV 房间**
   - 访问 `http://[服务器IP]:23862`
   - 创建或加入房间

2. **添加 WebDAV 资源**
   - 点击 "添加视频" → 选择 "WebDAV"
   - **服务器地址**: `http://[你的Tailscale地址]:5244`
   - **路径**: `/local`（或你在 Alist 中配置的路径）
   - 如果需要认证，输入 Alist 的用户名和密码

---

## 7. 常用管理命令

### 服务管理

```bash
# 启动所有服务
docker compose up -d

# 停止所有服务
docker compose down

# 重启所有服务
docker compose restart

# 重启特定服务
docker compose restart synctv

# 查看服务状态
docker compose ps

# 查看服务日志
docker compose logs -f [服务名]
```

### 数据备份

```bash
# 备份数据目录
tar -czf backup-$(date +%Y%m%d).tar.gz data/ synctv/

# 恢复数据
tar -xzf backup-YYYYMMDD.tar.gz
```

### 更新服务

```bash
# 拉取最新镜像
docker compose pull

# 重新创建并启动容器
docker compose up -d --force-recreate
```

---

## 8. 故障排查

### 端口冲突

如果遇到端口被占用：

```bash
# 查看端口占用
sudo netstat -tulpn | grep [端口号]

# 或使用 ss
sudo ss -tulpn | grep [端口号]
```

### 权限问题

如果遇到权限错误：

```bash
# 修复数据目录权限
sudo chown -R $USER:$USER data/ synctv/
```

### 查看容器日志

```bash
# 查看所有服务日志
docker compose logs

# 查看特定服务日志
docker compose logs synctv
docker compose logs alist

# 实时跟踪日志
docker compose logs -f synctv
```

### 无法访问服务

1. 检查防火墙规则
2. 确认 Tailscale 连接状态（如使用 Tailscale）
3. 检查容器是否正常运行：`docker compose ps`
4. 查看容器日志排查错误

---

## 9. 安全建议

1. **使用 Tailscale**：建议通过 Tailscale 内网访问，避免暴露公网端口
2. **防火墙配置**：限制端口访问，仅允许信任的 IP
3. **定期更新**：定期更新 Docker 镜像以获取安全补丁
4. **密码安全**：为各服务设置强密码
5. **数据备份**：定期备份 `data/` 目录

---

## 相关链接

- [SyncTV 官方文档](https://synctv.net/)
- [Alist 官方文档](https://alist.nn.ci/)
- [Uptime Kuma 文档](https://github.com/louislam/uptime-kuma)
- [Tailscale 文档](https://tailscale.com/kb/)
