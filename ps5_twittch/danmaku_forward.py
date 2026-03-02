# -*- coding: utf-8 -*-
import os
import asyncio
import logging
import requests
import json
import time
import threading
from collections import deque
from typing import Dict, Set
from datetime import datetime
from flask import Flask, jsonify, request, render_template_string

# ===================== 彻底屏蔽所有警告 =====================
import warnings
warnings.filterwarnings('ignore')
from urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# ===================== 全局配置（所有可配置项）=====================
CONFIG_FILE = os.getenv("CONFIG_FILE", "config.json")
# 所有可配置项的默认值（覆盖全部功能）
DEFAULT_CONFIG = {
    "WEB_PORT": 5000,
    "BILIBILI_ROOM_ID": B站直播间ID,
    "TWITCH_CHANNEL": "teittch用户名",
    "IRC_HOST": "0.0.0.0",
    "IRC_PORT": 17667,
    "DANMAKU_POLL_INTERVAL": 3,
    "MAX_SEEN_DANMAKU": 1000,
    "HEARTBEAT_TIMEOUT": 300,
    "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}
CONFIG = DEFAULT_CONFIG.copy()

# ===================== 全局变量（显式初始化，解决作用域问题）=====================
SEEN_DANMAKU_RND = set()  # 显式初始化空集合，避免作用域冲突
SEEN_DANMAKU_ORDER = deque()  # 记录弹幕ID顺序，便于按时间清理缓存
ACTIVE_CONNECTIONS = set()
IRC_RUNNING = False
DANMAKU_RUNNING = True

# ===================== 日志配置 =====================
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
logging.getLogger('requests').setLevel(logging.CRITICAL)
logging.getLogger('flask').setLevel(logging.CRITICAL)
logging.getLogger('werkzeug').setLevel(logging.CRITICAL)

logger = logging.getLogger("ps5-bilibili-danmaku")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s"))
logger.addHandler(handler)

os.makedirs("logs", exist_ok=True)

# ===================== 配置加载/保存（核心：支持全量配置）=====================
def load_config():
    """加载配置文件（缺失则用默认值）"""
    global CONFIG
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            loaded_config = json.load(f)
            # 合并配置：保留默认值，覆盖已配置项
            for key in DEFAULT_CONFIG.keys():
                if key in loaded_config:
                    CONFIG[key] = loaded_config[key]
    except Exception as e:
        # 配置文件不存在，生成默认配置
        save_config()
        logger.info(f"配置文件不存在，生成默认配置: {e}")
    logger.info(f"配置加载完成，当前直播间ID：{CONFIG['BILIBILI_ROOM_ID']}")

def save_config(new_config=None):
    """保存全量配置到文件"""
    global CONFIG
    if new_config:
        # 验证并更新配置（仅允许DEFAULT_CONFIG中的字段）
        for key, value in new_config.items():
            if key in DEFAULT_CONFIG:
                # 类型校验，避免配置错误
                if key in ["BILIBILI_ROOM_ID", "IRC_PORT", "DANMAKU_POLL_INTERVAL", 
                           "MAX_SEEN_DANMAKU", "HEARTBEAT_TIMEOUT", "WEB_PORT"]:
                    CONFIG[key] = int(value) if str(value).isdigit() else DEFAULT_CONFIG[key]
                else:
                    CONFIG[key] = value.strip() if isinstance(value, str) else value
    # 保存到文件
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(CONFIG, f, ensure_ascii=False, indent=4)
        logger.info(f"配置已保存：直播间ID={CONFIG['BILIBILI_ROOM_ID']}, IRC端口={CONFIG['IRC_PORT']}")
    except Exception as e:
        logger.error(f"保存配置失败: {e}")

# ===================== IRC客户端 =====================
class IRCClient:
    def __init__(self, reader, writer, server):
        self.reader = reader
        self.writer = writer
        self.server = server
        self.nick = ""
        self.user_ready = False
        self.welcomed = False
        self.peername = writer.get_extra_info("peername")
        self.last_active = datetime.now()
        self.auto_joined = False
        self.is_alive = True
        ACTIVE_CONNECTIONS.add(self.peername)

    def check_alive(self):
        """检查客户端是否存活"""
        if not self.writer or self.writer.is_closing():
            self.is_alive = False
            if self.peername in ACTIVE_CONNECTIONS: 
                ACTIVE_CONNECTIONS.discard(self.peername)
            return False
        # 超时清理
        if (datetime.now() - self.last_active).total_seconds() > CONFIG["HEARTBEAT_TIMEOUT"]:
            self.is_alive = False
            if self.peername in ACTIVE_CONNECTIONS: 
                ACTIVE_CONNECTIONS.discard(self.peername)
            logger.warning(f"PS5({self.peername}) 连接超时，已清理")
            return False
        return True

    async def send_safe(self, data):
        """安全发送数据到PS5，返回是否发送成功"""
        if not self.check_alive():
            return False
        if not data.endswith("\r\n"): 
            data += "\r\n"
        try:
            self.writer.write(data.encode('utf-8'))
            await self.writer.drain()
            self.last_active = datetime.now()
            return True
        except Exception as e:
            self.is_alive = False
            if self.peername in ACTIVE_CONNECTIONS: 
                ACTIVE_CONNECTIONS.discard(self.peername)
            logger.error(f"发送数据到PS5({self.peername})失败: {e}")
            return False

    async def auto_join_channel(self):
        """自动加入指定IRC频道"""
        if self.auto_joined or not self.check_alive(): 
            return
        if not self.nick:
            return
        target = f"#{CONFIG['TWITCH_CHANNEL']}"
        self.server.clients[target] = self
        # 发送JOIN指令
        await self.send_safe(f":{self.nick}!ps5@tmi.twitch.tv JOIN {target}")
        await self.send_safe(f":tmi.twitch.tv 353 {self.nick} = {target} :{self.nick}")
        await self.send_safe(f":tmi.twitch.tv 366 {self.nick} {target} :End of /NAMES list")
        self.auto_joined = True
        logger.info(f"PS5({self.peername}) 已加入频道 {target}")

    async def send_welcome_if_ready(self):
        """尽量兼容不同客户端的登录时序，满足条件后再发欢迎"""
        if self.welcomed or not self.nick or not self.user_ready:
            return
        await self.send_safe(f":tmi.twitch.tv 001 {self.nick} :Welcome to Twitch!")
        await self.send_safe(f":tmi.twitch.tv 002 {self.nick} :Your host is tmi.twitch.tv")
        await self.send_safe(f":tmi.twitch.tv 003 {self.nick} :This server is local bridge")
        await self.send_safe(f":tmi.twitch.tv 004 {self.nick} tmi.twitch.tv")
        self.welcomed = True
        await self.auto_join_channel()

    async def handle_message(self, line):
        """处理PS5发送的IRC指令"""
        if not line or not self.check_alive(): 
            return
        parts = line.split()
        if not parts: 
            return
        cmd = parts[0].upper()
        self.last_active = datetime.now()

        if cmd == "NICK" and len(parts) >= 2:
            self.nick = parts[1]
            logger.info(f"PS5({self.peername}) 设置昵称: {self.nick}")
            await self.send_welcome_if_ready()

        elif cmd == "USER":
            # USER到达后标记就绪，按标准再发欢迎
            self.user_ready = True
            await self.send_welcome_if_ready()

        elif cmd == "PASS":
            # 兼容Twitch IRC登录流程，PASS无需校验
            return

        elif cmd == "CAP":
            # 兼容CAP REQ，返回ACK避免客户端断连
            if len(parts) >= 3 and parts[1].upper() == "REQ":
                req_caps = " ".join(parts[2:]).lstrip(":").strip()
                if req_caps:
                    await self.send_safe(f":tmi.twitch.tv CAP * ACK :{req_caps}")
            elif len(parts) >= 2 and parts[1].upper() == "END":
                await self.send_welcome_if_ready()

        elif cmd == "JOIN" and len(parts) >= 2:
            # 若客户端主动JOIN，回包并覆盖目标频道映射
            target = parts[1]
            if not target.startswith("#"):
                target = f"#{target}"
            self.server.clients[target] = self
            await self.send_safe(f":{self.nick}!ps5@tmi.twitch.tv JOIN {target}")
            await self.send_safe(f":tmi.twitch.tv 353 {self.nick} = {target} :{self.nick}")
            await self.send_safe(f":tmi.twitch.tv 366 {self.nick} {target} :End of /NAMES list")
            logger.info(f"PS5({self.peername}) 主动JOIN频道 {target}")

        elif cmd == "PING":
            # 响应PING指令，保持连接
            ping_arg = parts[1] if len(parts) >= 2 else "tmi.twitch.tv"
            await self.send_safe(f"PONG :{ping_arg}")

        elif cmd == "PONG":
            # PS5响应服务端心跳即可，last_active已在函数开头刷新
            return

    async def run(self):
        """客户端主循环"""
        heartbeat_interval = max(15, min(60, int(CONFIG["HEARTBEAT_TIMEOUT"]) // 4))
        try:
            while self.check_alive():
                try:
                    # 空闲一段时间后主动发PING，避免长时间无弹幕导致误超时
                    data = await asyncio.wait_for(self.reader.readline(), timeout=heartbeat_interval)
                    if not data:
                        break
                    line = data.decode('utf-8', errors='ignore').strip()
                    if line:
                        await self.handle_message(line)
                except asyncio.TimeoutError:
                    if not self.check_alive():
                        break
                    await self.send_safe("PING :tmi.twitch.tv")
        except Exception as e:
            logger.error(f"PS5({self.peername}) 连接异常: {e}")
        finally:
            self.is_alive = False
            if self.peername in ACTIVE_CONNECTIONS: 
                ACTIVE_CONNECTIONS.discard(self.peername)
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except:
                pass
            logger.info(f"PS5({self.peername}) 连接已关闭")

class IRCServer:
    def __init__(self):
        self.clients: Dict[str, IRCClient] = {}  # 频道->客户端映射
        self.connected_clients: Set[IRCClient] = set()  # 所有已连接客户端（用于兜底转发）

    async def start(self):
        """启动IRC服务器"""
        global IRC_RUNNING
        while True:
            try:
                server = await asyncio.start_server(
                    self.handle_client,
                    CONFIG["IRC_HOST"],
                    CONFIG["IRC_PORT"],
                    reuse_address=True,
                    reuse_port=True
                )
                IRC_RUNNING = True
                logger.info(f"IRC服务已启动: {CONFIG['IRC_HOST']}:{CONFIG['IRC_PORT']}")
                async with server:
                    await server.serve_forever()
            except Exception as e:
                IRC_RUNNING = False
                logger.error(f"IRC服务器启动失败: {e}")
                await asyncio.sleep(5)

    async def handle_client(self, reader, writer):
        """处理新的PS5连接"""
        client = IRCClient(reader, writer, self)
        self.connected_clients.add(client)
        logger.info(f"检测到PS5连接: {client.peername}")
        try:
            await client.run()
        finally:
            self.connected_clients.discard(client)

    async def send_danmaku(self, user, text):
        """转发弹幕到PS5"""
        target = f"#{CONFIG['TWITCH_CHANNEL']}"
        client = self.clients.get(target)
        
        # 找不到指定频道则用第一个活跃客户端
        if not client:
            for c in self.clients.values():
                if c.check_alive():
                    client = c
                    break

        # 再兜底：频道映射还没建立时，从已连接客户端里挑一个存活的
        if not client:
            for c in list(self.connected_clients):
                if c.check_alive():
                    client = c
                    # 尝试自动加入目标频道，后续转发会走频道映射
                    await c.auto_join_channel()
                    break
        
        if not client:
            logger.warning(f"无活跃PS5客户端，弹幕[{user}:{text}]转发失败")
            return
        
        # 构造Twitch格式的弹幕消息
        msg = f":{user}!{user}@tmi.twitch.tv PRIVMSG {target} :{text}"
        sent_ok = await client.send_safe(msg)
        if sent_ok:
            logger.info(f"转发弹幕 [{user}]: {text}")
        else:
            logger.warning(f"转发失败（连接不可用）[{user}]: {text}")

# ===================== B站弹幕抓取（核心修复SEEN_DANMAKU_RND）=====================
# 全局Session，复用连接
SESSION = requests.Session()
SESSION.verify = False  # 禁用SSL验证

def update_session_headers():
    """更新请求头（适配配置中的USER_AGENT）"""
    SESSION.headers.update({
        "User-Agent": CONFIG["USER_AGENT"],
        "Referer": f"https://live.bilibili.com/{CONFIG['BILIBILI_ROOM_ID']}"
    })

def get_danmaku():
    """抓取B站直播间弹幕（修复SEEN_DANMAKU_RND作用域）"""
    global DANMAKU_RUNNING, SEEN_DANMAKU_RND, SEEN_DANMAKU_ORDER  # 显式声明使用全局变量
    try:
        DANMAKU_RUNNING = True
        update_session_headers()
        
        # B站弹幕接口
        url = f"https://api.live.bilibili.com/xlive/web-room/v1/dM/gethistory?roomid={CONFIG['BILIBILI_ROOM_ID']}"
        response = SESSION.get(url, timeout=10)
        response.raise_for_status()  # 触发HTTP错误
        data = response.json()

        new_danmakus = []
        if data.get("code") == 0:
            # 兼容接口返回的两种数据格式
            danmaku_list = data["data"].get("room", []) or data["data"].get("list", [])
            
            for dm in danmaku_list:
                # 生成唯一ID去重（避免重复抓取）
                dm_id = f"{dm.get('timeline', dm.get('ctime', ''))}_{dm.get('text', '')}"
                
                # 确保SEEN_DANMAKU_RND是集合类型
                if not isinstance(SEEN_DANMAKU_RND, set):
                    SEEN_DANMAKU_RND = set()
                    SEEN_DANMAKU_ORDER = deque()
                
                if dm_id not in SEEN_DANMAKU_RND:
                    SEEN_DANMAKU_RND.add(dm_id)
                    SEEN_DANMAKU_ORDER.append(dm_id)
                    uname = dm.get("nickname", dm.get("uname", "未知用户"))
                    content = dm.get("text", "").strip()
                    if content:  # 过滤空弹幕
                        new_danmakus.append((uname, content))
        
        # 清理旧的弹幕ID（避免内存溢出）
        max_cache = max(1, int(CONFIG["MAX_SEEN_DANMAKU"]))
        if len(SEEN_DANMAKU_RND) > max_cache:
            keep_size = max(1, int(max_cache * 0.8))
            # 按进入时间清理最旧的弹幕ID，避免set无序导致“最新”不准确
            while len(SEEN_DANMAKU_RND) > keep_size and SEEN_DANMAKU_ORDER:
                old_id = SEEN_DANMAKU_ORDER.popleft()
                SEEN_DANMAKU_RND.discard(old_id)
            logger.debug(f"清理弹幕缓存，当前缓存数: {len(SEEN_DANMAKU_RND)}")
        
        if new_danmakus:
            logger.info(f"抓取到{len(new_danmakus)}条新弹幕")
        return new_danmakus
    
    except Exception as e:
        DANMAKU_RUNNING = False
        logger.error(f"抓取弹幕失败: {str(e)}")
        return []

async def danmaku_worker(irc_srv):
    """弹幕抓取工作线程"""
    logger.info(f"开始监听B站直播间 {CONFIG['BILIBILI_ROOM_ID']}")
    await asyncio.sleep(2)  # 等待IRC服务启动
    
    while True:
        try:
            # requests是阻塞调用，放到线程池避免卡住asyncio事件循环
            new_danmakus = await asyncio.to_thread(get_danmaku)
            for user, text in new_danmakus:
                await irc_srv.send_danmaku(user, text)
        except Exception as e:
            logger.error(f"弹幕处理异常: {e}")
        # 按配置的间隔抓取
        await asyncio.sleep(CONFIG["DANMAKU_POLL_INTERVAL"])

# ===================== Web服务（全配置项可视化管理）=====================
def start_web():
    """启动Web配置界面（所有配置项可修改）"""
    web_port = CONFIG.get("WEB_PORT", 5000)
    app = Flask("ps5-danmaku-web")

    # 完整的Web配置界面（内置HTML，无需外部文件）
    WEB_HTML = """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>PS5-B站弹幕转发 - 全配置管理</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: Arial, sans-serif; max-width: 1000px; margin: 20px auto; padding: 0 20px; background: #f5f5f5; }
            .container { background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            h1 { text-align: center; color: #333; margin-bottom: 30px; }
            .config-group { margin-bottom: 25px; }
            .config-group h3 { color: #007bff; margin-bottom: 15px; border-bottom: 2px solid #eee; padding-bottom: 5px; }
            .form-item { display: flex; align-items: center; margin-bottom: 12px; }
            .form-item label { width: 200px; font-weight: 500; color: #555; }
            .form-item input { flex: 1; padding: 8px 12px; border: 1px solid #ddd; border-radius: 4px; font-size: 14px; }
            .form-item input:focus { outline: none; border-color: #007bff; box-shadow: 0 0 0 2px rgba(0,123,255,0.1); }
            .btn-save { width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; margin-top: 20px; }
            .btn-save:hover { background: #0056b3; }
            .status-box { margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 6px; }
            .status-box h3 { color: #28a745; margin-bottom: 15px; }
            .status-item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #eee; }
            .status-item span:first-child { color: #555; }
            .status-item span:last-child { font-weight: 500; color: #333; }
            .msg { text-align: center; margin-top: 15px; padding: 10px; border-radius: 4px; display: none; }
            .msg.success { background: #d4edda; color: #155724; display: block; }
            .msg.error { background: #f8d7da; color: #721c24; display: block; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>PS5-B站弹幕转发 - 全配置管理</h1>
            
            <!-- 配置表单 -->
            <div class="config-group">
                <h3>基础配置</h3>
                <div class="form-item">
                    <label>B站直播间ID：</label>
                    <input type="number" id="BILIBILI_ROOM_ID" value="{{ BILIBILI_ROOM_ID }}" placeholder="例如：669827">
                </div>
                <div class="form-item">
                    <label>PS5 IRC频道名：</label>
                    <input type="text" id="TWITCH_CHANNEL" value="{{ TWITCH_CHANNEL }}" placeholder="例如：yu332506767">
                </div>
                <div class="form-item">
                    <label>IRC服务监听地址：</label>
                    <input type="text" id="IRC_HOST" value="{{ IRC_HOST }}" placeholder="例如：0.0.0.0">
                </div>
                <div class="form-item">
                    <label>IRC服务端口：</label>
                    <input type="number" id="IRC_PORT" value="{{ IRC_PORT }}" placeholder="例如：17667">
                </div>
            </div>

            <div class="config-group">
                <h3>高级配置</h3>
                <div class="form-item">
                    <label>Web服务端口：</label>
                    <input type="number" id="WEB_PORT" value="{{ WEB_PORT }}" placeholder="例如：5000">
                </div>
                <div class="form-item">
                    <label>弹幕抓取间隔(秒)：</label>
                    <input type="number" id="DANMAKU_POLL_INTERVAL" value="{{ DANMAKU_POLL_INTERVAL }}" min="1" max="10" placeholder="例如：3">
                </div>
                <div class="form-item">
                    <label>最大弹幕缓存数：</label>
                    <input type="number" id="MAX_SEEN_DANMAKU" value="{{ MAX_SEEN_DANMAKU }}" placeholder="例如：1000">
                </div>
                <div class="form-item">
                    <label>PS5连接超时(秒)：</label>
                    <input type="number" id="HEARTBEAT_TIMEOUT" value="{{ HEARTBEAT_TIMEOUT }}" placeholder="例如：300">
                </div>
                <div class="form-item">
                    <label>请求User-Agent：</label>
                    <input type="text" id="USER_AGENT" value="{{ USER_AGENT }}" placeholder="浏览器标识">
                </div>
            </div>

            <button class="btn-save" onclick="saveConfig()">保存所有配置</button>
            <div id="msg" class="msg"></div>

            <!-- 运行状态 -->
            <div class="status-box">
                <h3>当前运行状态</h3>
                <div class="status-item">
                    <span>活跃PS5客户端数：</span>
                    <span id="active_clients">{{ active_clients }}</span>
                </div>
                <div class="status-item">
                    <span>IRC服务状态：</span>
                    <span id="irc_running">{{ "运行中" if irc_running else "已停止" }}</span>
                </div>
                <div class="status-item">
                    <span>弹幕抓取状态：</span>
                    <span id="danmaku_running">{{ "运行中" if danmaku_running else "已停止" }}</span>
                </div>
                <div class="status-item">
                    <span>最后更新时间：</span>
                    <span id="update_time">{{ update_time }}</span>
                </div>
            </div>
        </div>

        <script>
            // 保存所有配置
            function saveConfig() {
                const config = {};
                // 获取所有输入框的值
                const inputs = document.querySelectorAll('input');
                inputs.forEach(input => {
                    config[input.id] = input.value;
                });

                // 发送保存请求
                fetch('/save_config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                }).then(res => res.json()).then(data => {
                    const msgEl = document.getElementById('msg');
                    if (data.code === 0) {
                        msgEl.className = 'msg success';
                        msgEl.textContent = data.msg;
                        // 2秒后刷新页面
                        setTimeout(() => window.location.reload(), 2000);
                    } else {
                        msgEl.className = 'msg error';
                        msgEl.textContent = data.msg;
                    }
                    // 3秒后隐藏提示
                    setTimeout(() => msgEl.style.display = 'none', 3000);
                }).catch(err => {
                    const msgEl = document.getElementById('msg');
                    msgEl.className = 'msg error';
                    msgEl.textContent = '保存失败：' + err.message;
                });
            }

            // 定时刷新状态
            function refreshStatus() {
                fetch('/status').then(res => res.json()).then(data => {
                    document.getElementById('active_clients').textContent = data.active_clients;
                    document.getElementById('irc_running').textContent = data.irc_running ? '运行中' : '已停止';
                    document.getElementById('danmaku_running').textContent = data.danmaku_running ? '运行中' : '已停止';
                    document.getElementById('update_time').textContent = new Date().toLocaleString();
                });
            }

            // 页面加载后刷新状态，之后每5秒刷新一次
            window.onload = function() {
                refreshStatus();
                setInterval(refreshStatus, 5000);
            };
        </script>
    </body>
    </html>
    """

    # Web首页（配置+状态）
    @app.route('/')
    def index():
        # 组装页面渲染数据
        render_data = {
            "BILIBILI_ROOM_ID": CONFIG["BILIBILI_ROOM_ID"],
            "TWITCH_CHANNEL": CONFIG["TWITCH_CHANNEL"],
            "IRC_HOST": CONFIG["IRC_HOST"],
            "IRC_PORT": CONFIG["IRC_PORT"],
            "WEB_PORT": CONFIG["WEB_PORT"],
            "DANMAKU_POLL_INTERVAL": CONFIG["DANMAKU_POLL_INTERVAL"],
            "MAX_SEEN_DANMAKU": CONFIG["MAX_SEEN_DANMAKU"],
            "HEARTBEAT_TIMEOUT": CONFIG["HEARTBEAT_TIMEOUT"],
            "USER_AGENT": CONFIG["USER_AGENT"],
            "active_clients": len(ACTIVE_CONNECTIONS),
            "irc_running": IRC_RUNNING,
            "danmaku_running": DANMAKU_RUNNING,
            "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return render_template_string(WEB_HTML, **render_data)

    # 保存配置接口
    @app.route('/save_config', methods=['POST'])
    def save_config_api():
        try:
            new_config = request.get_json()
            if not new_config:
                return jsonify({"code": 1, "msg": "配置数据为空"})
            
            save_config(new_config)
            return jsonify({"code": 0, "msg": "所有配置保存成功！2秒后自动刷新页面"})
        except Exception as e:
            return jsonify({"code": 1, "msg": f"保存配置失败：{str(e)}"})

    # 状态查询接口
    @app.route('/status')
    def get_status():
        return jsonify({
            "active_clients": len(ACTIVE_CONNECTIONS),
            "irc_running": IRC_RUNNING,
            "danmaku_running": DANMAKU_RUNNING,
            "web_port": web_port,
            "room_id": CONFIG["BILIBILI_ROOM_ID"]
        })

    # 启动Web服务（禁用调试模式，避免重复启动）
    logger.info(f"Web配置界面已启动: http://0.0.0.0:{web_port}")
    app.run(
        host="0.0.0.0", 
        port=web_port, 
        debug=False, 
        use_reloader=False,  # 关键：禁用自动重载，避免线程冲突
        threaded=True        # 启用多线程处理请求
    )

# ===================== 主程序入口 =====================
async def main():
    """主程序（IRC服务+弹幕抓取）"""
    load_config()
    # 初始化IRC服务器
    irc_server = IRCServer()
    # 启动IRC服务和弹幕抓取
    await asyncio.gather(
        irc_server.start(),
        danmaku_worker(irc_server)
    )

if __name__ == "__main__":
    # 1. 先加载配置（确保所有配置项存在）
    load_config()
    
    # 2. 启动Web服务（独立线程，不阻塞主程序）
    web_thread = threading.Thread(target=start_web, daemon=True)
    web_thread.start()
    
    # 3. 启动主程序（IRC+弹幕抓取）
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("程序被手动终止")
    except Exception as e:
        logger.error(f"主程序异常: {e}")