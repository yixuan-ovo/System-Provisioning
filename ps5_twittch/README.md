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

## 网络环境（二选一）

本项目的核心仍是：**用本机 `dnsmasq` 把 Twitch 相关域名解析到 Docker 所在电脑**，再由容器完成 RTMP 转推与弹幕 IRC 桥接。  
下面两种网络方式都已跑通，请按你的实际环境选一种；**步骤 1～4、6～7 两种方案相同**，差别主要在 **步骤 5**。

| 方案 | 适用场景 | 外网/代理由谁处理 |
|------|----------|-------------------|
| **A：ImmortalWrt 路由器** | 家庭路由器已刷 ImmortalWrt，并做过 DNS/透明代理等配置（本文最初编写与长期验证环境） | 路由器侧统一处理 |
| **B：Clash Verge + PS5 系统代理** | 无 ImmortalWrt，在 **跑着 Docker 的 Windows 电脑** 上用 Clash Verge 出境 | Clash 局域网代理 + PS5 填代理 |

---

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

1. `data/config.json`（弹幕服务 V2：WebSocket + 扫码登录，配置挂载在 `/app/config.json`）  
   - `BILIBILI_ROOM_ID`：改成你的 B 站直播间 ID。  
   - `TWITCH_CHANNEL`：改成你要给 PS5 使用的频道名（建议只用英文/数字/下划线）。  
   - `IRC_PORT` 保持 `17667`（与端口映射 `6667:17667` 一致）。  
   - 登录态保存在 `data/bili_cookies.json`，也可在 Web `http://<IP>:15500/` 扫码。  

2. `data/dnsmasq.conf`  
   - 把下面两个地址都改成你的电脑局域网 IP：  
     - `address=/live-video.net/<你的电脑局域网IP>`  
     - `address=/irc.twitch.tv/<你的电脑局域网IP>`  

3. `data/nginx.conf`  
   - 找到 `push rtmp://...` 这一行。  
   - 替换为你自己的 B 站推流地址（整串都要正确，包含 key 参数）。

## 3) 启动容器

- 在 `ps5_twittch` 目录执行：
  - 全量：`docker compose up -d --build`
  - 仅重建弹幕：`docker compose up -d --build ps5-bilibili-danmaku`
- Web 保存配置后需重启弹幕容器：`docker compose restart ps5-bilibili-danmaku`
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

## 5) 配置 PS5 网络（重点，按所选方案操作）

两种方案都需要：**PS5 能连上 Docker 电脑**，且 **DNS 指向 Docker 所在电脑的局域网 IP**（让 `live-video.net`、`irc.twitch.tv` 解析到本机 `dnsmasq`）。  
在 PS5「设置 → 网络 → 设定互联网连接」中，建议为 PS5 配置固定 IP（或与路由器 DHCP 保留一致），并记下该 IP。

### 5A) 方案 A：ImmortalWrt 家庭路由器环境

- 让 PS5 使用能访问到本机 `dnsmasq` 的 DNS。常见做法二选一：  
  - 在 ImmortalWrt / 路由器里把局域网 DNS 指向你的电脑 IP；  
  - 或在 PS5 网络设置里**手动把 DNS 填成 Docker 电脑的局域网 IP**（主、备 DNS 可都填同一地址）。  
- **不需要**在 PS5 里再开「代理服务器」（由路由器侧处理出境即可）。  
- 配完 DNS 后，建议 PS5 断网重连一次，确保新 DNS 生效。

### 5B) 方案 B：Clash Verge + PS5 系统代理（已验证可正常推流）

适用于：没有 ImmortalWrt，只在 **开着 Docker 的那台 Windows** 上跑 Clash Verge。

#### 5B-1) Clash Verge（Docker 所在电脑）

在 Clash Verge 中建议如下（与「系统代理 / 虚拟网卡」方案区分开）：

| 项 | 建议设置 |
|----|----------|
| 系统代理 | **关闭** |
| 虚拟网卡（TUN） | **关闭** |
| 局域网连接 / 允许局域网（Allow LAN） | **开启** |
| 代理模式 | **全局**（Global） |
| 节点 | 选中一个**可用**节点 |

在 Clash Verge「设置」里查看并记下 **混合端口** 或 **HTTP 代理端口**（不同版本名称略有差异，常见为 `7897`，**以你本机界面显示为准**）。  
同时确认 Windows 防火墙允许该端口的**局域网入站**（否则 PS5 连不上本机 Clash）。

#### 5B-2) PS5 网络

1. **DNS**（与方案 A 相同，必须做）：  
   - 主 DNS（必要时副 DNS 也）填 **Docker 电脑的局域网 IP**，使 Twitch 域名解析到本机容器。  
2. **代理服务器**（本方案关键）：  
   - 在 PS5 同一网络连接里打开 **「使用代理服务器」**；  
   - **地址**：Clash 所在电脑的局域网 IP（与 Docker 为同一台机器时，即 Docker 电脑 IP）；  
   - **端口**：Clash Verge 里记下的代理端口（见 5B-1）。  
3. 保存后建议 PS5 **断网重连** 一次，再进入下一步重开播。

> 说明：方案 B 下 PS5 的出境流量经 Clash 所选节点；Twitch 推流/IRC 相关域名仍由本机 `dnsmasq` 劫持到 Docker，二者配合使用。

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

## 注意事项

- **方案 A** 依赖家庭 ImmortalWrt/路由器侧网络配置；**方案 B** 依赖 Clash 局域网代理与 PS5 代理项填写正确，且 Clash 需保持运行。  
- 无论哪种方案，都最依赖 DNS：`dnsmasq.conf` 里的 IP 一旦变了就会失效。  
- 更换网络（有线/Wi-Fi 切换、路由器重启、DHCP 重新分配）后，要重新检查 `data/dnsmasq.conf`。  
- Windows 防火墙至少放行 `6667/TCP`、`1935/TCP`、`53/UDP`，否则 PS5 可能能开播但无法回显弹幕。  
- `data/nginx.conf` 含推流 key，`docker-compose.yml` 有管理账号密码，请勿公开上传。  
- `./data` 与 `./logs` 是排障依据，首次跑通前不要随意删除。  
- 如果 `status` 正常但不转发，优先看是否出现“无活跃PS5客户端”，通常是 DNS 未生效或 PS5 未重开播。
- ### 增加心跳包，依据设置的连接超时(秒)动态计算保活时间间隔，最短不会低于15s，最长不会超过60s

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
- **方案 B 排障**：推流异常时先确认 Clash「局域网连接」已开、模式为全局、节点可用，且 PS5 代理地址/端口与 Clash 设置一致；DNS 仍须指向 Docker 电脑 IP。
