# 本项目用于免采集卡实现PS5在 B 站直播并且将 B 站直播弹幕转发到 PS5 直播聊天显示。

---

## 项目来源声明

本项目为个人学习与实践用途，基于以下两个开源项目的思路与实现进行适配和整合：

- [ProgramRipper/BLiveWeb](https://github.com/ProgramRipper/BLiveWeb)
- [IceNoproblem/PS5BiliDanmaku](https://github.com/IceNoproblem/PS5BiliDanmaku)

如本项目中涉及对上述项目代码或思路的引用，版权与许可归原项目及其许可证所有。

感谢原项目作者和社区贡献者的开源分享。

---

# 详细使用方法（按步骤照做）

## 0) 先理解这套方案在做什么

- PS5 直播时会连接 Twitch 的 RTMP 与 IRC。  
- 本项目通过 `dnsmasq` 把这些域名解析到你的电脑局域网 IP，让 PS5 实际连到你本机容器。  
- `ps5living` 负责 RTMP 转推到 B 站；`ps5-bilibili-danmaku` 负责抓取 B 站弹幕并通过本地 IRC 回给 PS5。

## 1) 前置准备（第一次必看）

- 你的电脑与 PS5 在同一局域网。  
- 电脑已安装 Docker Desktop，并确保 Docker 正在运行。  
- 你有 B 站直播间，并拿到了可用的推流地址（包含 `streamname/key`）。  
- 建议给电脑配置相对固定的局域网 IP（或在路由器做 DHCP 保留），避免 IP 变化导致失效。  
- 先记下电脑局域网 IP（Windows 可用 `ipconfig` 查看，通常是 `192.168.x.x`）。
- CLone本项目放在一个文件夹内，在文件夹内启动cmd
- #### 如果粉丝数不够获取推流码建议使用[这个项目获取推流码](https://github.com/ProgramRipper/BLiveWeb)

## 2) 修改 3 个关键配置文件（必须）

1. `data/config.json`  
   - `BILIBILI_ROOM_ID`：改成你的 B 站直播间 ID。  
   - `TWITCH_CHANNEL`：改成你要给 PS5 使用的频道名（建议只用英文/数字/下划线）。  

2. `data/dnsmasq.conf`  
   - 把下面两个地址都改成你的电脑局域网 IP：  
     - `address=/live-video.net/<你的电脑局域网IP>`  
     - `address=/irc.twitch.tv/<你的电脑局域网IP>`  

3. `data/nginx.conf`  
   - 找到 `push rtmp://...` 这一行。  
   - 替换为你自己的 B 站推流地址（整串都要正确，包含 key 参数）。

## 3) 启动容器

- 在 `ps5_twittch` 目录执行：
  - `docker compose up -d --build`
- 成功标志：
  - `docker compose ps` 里 `ps5-bilibili-danmaku`、`ps5living`、`dnsmasq` 都是 `Up` 状态。

## 4) 先在电脑侧做一次自检

- 打开配置页：`http://<你的电脑局域网IP>:15500/`  
- 打开状态接口：`http://<你的电脑局域网IP>:15500/status`  
- 成功标志：
  - `irc_running=true`
  - `danmaku_running=true`

如果这里不正常，先不要去 PS5，优先看日志：

- `docker compose logs -f ps5-bilibili-danmaku`

## 5) 配置 PS5 网络（重点）

- 让 PS5 使用能访问到本机 `dnsmasq` 的 DNS。常见做法二选一：  
  - 在路由器里把局域网 DNS 指向你的电脑 IP；  
  - 或在 PS5 网络设置里手动把 DNS 填成你的电脑 IP。  
- 配完 DNS 后，建议 PS5 断网重连一次，确保新 DNS 生效。

## 6) 在 PS5 重新开播触发重连

- 先停止当前直播，再重新开始直播（不要只保持原会话）。  
- 这一步会触发 PS5 重新解析域名并连接你的本地 IRC/RTMP。

## 7) 做最终验证

- 在 B 站直播间发送 1 条测试弹幕。  
- 查看日志：
  - `docker compose logs -f ps5-bilibili-danmaku`
- 成功标志（至少看到其中几条）：
  - `检测到PS5连接`
  - `已加入频道`
  - `抓取到N条新弹幕`
  - `转发弹幕 [...]`

## 注意事项（新手最容易踩坑）

- 这套方案最依赖 DNS，`dnsmasq.conf` 里的 IP 一旦变了就会失效。  
- 更换网络（有线/Wi-Fi 切换、路由器重启、DHCP 重新分配）后，要重新检查 `data/dnsmasq.conf`。  
- Windows 防火墙至少放行 `6667/TCP`、`1935/TCP`、`53/UDP`，否则 PS5 可能能开播但无法回显弹幕。  
- `data/nginx.conf` 含推流 key，`docker-compose.yml` 有管理账号密码，请勿公开上传。  
- `./data` 与 `./logs` 是排障依据，首次跑通前不要随意删除。  
- 如果 `status` 正常但不转发，优先看是否出现“无活跃PS5客户端”，通常是 DNS 未生效或 PS5 未重开播。

---

# PS5 B站弹幕转发（排障清单）

## 当前已验证可用的关键配置

- `ps5-bilibili-danmaku`
  - `15500:5000`（Web 配置页）
  - `6667:17667`（IRC 桥接）
- `ps5living`
  - `1935:1935`（RTMP 推流）
  - `17890:80`（RTMP 状态页）
- `dnsmasq`
  - `53:53/udp`
  - `18081:8080`
  - 挂载 `./data/dnsmasq.conf:/etc/dnsmasq.conf:ro`
- `ps5living`
  - 挂载 `./data/nginx.conf:/etc/nginx/nginx.conf:ro`

`data/dnsmasq.conf` 关键规则：

- `address=/live-video.net/<你的电脑局域网IP>`
- `address=/irc.twitch.tv/<你的电脑局域网IP>`

## 一键健康检查

在项目目录执行：

- `docker compose ps`
- `curl http://127.0.0.1:15500/status`
- `curl http://127.0.0.1:17890/`
- `nslookup irc.twitch.tv 127.0.0.1`
- `nslookup ingest.global-contribute.live-video.net 127.0.0.1`

期望：

- `status` 中 `irc_running=true`、`danmaku_running=true`
- `nslookup` 两个域名都返回你的局域网 IP

## 日志判读速查

查看日志：

- `docker compose logs -f ps5-bilibili-danmaku`

### 1) 看到「抓取到N条新弹幕」

说明 B 站抓取正常。

### 2) 看到「无活跃PS5客户端，弹幕[...]转发失败」

说明 IRC 客户端未连上或未完成可转发状态，优先检查：

- `status` 中 `active_clients` 是否大于 0
- DNS 是否把 `irc.twitch.tv` 解析到你的局域网 IP
- PS5 是否完整重开直播（触发重新解析/重连）
- Windows 防火墙是否放行 `6667/TCP`

### 3) 看到「检测到PS5连接」「设置昵称」「已加入频道」

说明 IRC 通道已建立，后续应看到「转发弹幕 [...]」。

### 4) RTMP 页面 `Accepted: 0`

说明 PS5 没连上本地推流入口，优先检查：

- `1935` 端口是否已映射并监听
- DNS 中 `ingest...live-video.net` 是否解析到你的局域网 IP
- 局域网内 PS5 到你电脑的网络连通性

## 常用恢复步骤

1. `docker compose up -d --build`
2. 在 PS5 上停止直播并重新开始直播
3. 发送一条 B 站弹幕测试
4. 观察 `ps5-bilibili-danmaku` 日志是否出现「转发弹幕」

## 备注

- 日志中 `Invalid -W option ignored...` 属于告警参数格式问题，通常不影响主功能。
- 若改了局域网（比如从有线切换 Wi-Fi），记得同步更新 `data/dnsmasq.conf` 里的局域网 IP。
