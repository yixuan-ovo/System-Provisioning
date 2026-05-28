# PS5 哔哩哔哩弹幕 v2（含 RTMP 监控）

弹幕转发 + DNS 劫持 + RTMP 中继 + **Web 面板实时显示推流状态**。

## 服务架构

| 容器 | 服务名 | 端口（宿主机） | 说明 |
|------|--------|----------------|------|
| ps5-Danmaku | `ps5-bilibili-danmaku` | 15500, 6667 | Web 管理 + B 站弹幕 IRC |
| ps5living-bao3 | `ps5living` | 1935, 17890 | PS5 RTMP 推流与中继 |
| ps5-rtmp-monitor | `rtmp-monitor` | — | 轮询 RTMP 统计并更新 Web |
| ps5living-dnsmasq | `dnsmasq` | 53, 18081 | DNS 劫持配置 |

## 快速开始

1. 编辑 `data/dnsmasq.conf`：填写路由器网关与 NAS/本机局域网 IP。
2. 编辑 `data/nginx.conf`：将 `push rtmp://<推流地址>` 改为你的 B 站推流地址。
3. 编辑 `data/config.json`：填写 B 站直播间 ID 等。
4. 启动：

```bash
cd ps5_twittch/danmaku-v2
docker compose up -d --build
```

5. 浏览器打开 `http://<宿主机IP>:15500`，配置直播间并保存后按提示重启弹幕容器。
6. 将 PS5 的 DNS 指向本机 `53` 端口（或使用 dnsmasq Web `18081` 管理）。

## RTMP 相关

- **推流地址（PS5）**：`rtmp://<宿主机IP>:1935/app/<推流码>`（推流码在 Web「RTMP 推流状态」中显示）
- **统计页（排查用）**：`http://<宿主机IP>:17890/`（nginx-rtmp XML）
- **监控日志**：`docker compose logs -f rtmp-monitor`

### 调试 RTMP 不显示

```bash
# 查看监控是否连上 RTMP / 弹幕 API
docker compose logs -f rtmp-monitor

# 手动看统计 XML
curl http://127.0.0.1:17890/

# 看 API 当前状态
curl http://127.0.0.1:15500/api/rtmp/status
```

启用调试版监控：在 `docker-compose.yml` 中将 `rtmp-monitor` 的 `command` 改为 `monitor_rtmp_debug.py`，并设置 `DEBUG_MODE=true`。

## 本地运行（不用 Docker）

```bash
pip install -r requirements.txt
python danmaku_forward.py
# 另开终端（需本机有 RTMP 服务且统计页可访问）：
python monitor_rtmp.py
```

环境变量示例：`RTMP_MONITOR_URL=http://127.0.0.1:17890`、`DANMAKU_API_URL=http://127.0.0.1:5000/api/rtmp/status/update`

## 常用命令

```bash
docker compose ps
docker compose logs -f ps5-bilibili-danmaku
docker compose restart rtmp-monitor
docker compose down
```
