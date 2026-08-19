import json
import os
import re
import socket
import sys
import time
import urllib.request
from pathlib import Path
import RndPic
import BiliCatcher

"""
    群聊 @<机器人账号><消息> 或私聊直接发送 <消息>：调用LLM进行对话，每个群聊、私聊都视为不同的会话，最多保留50轮上下文，超过范围自动重置
    #点赞：给请求者的QQ点赞
    #点歌 <关键词>：从B站爬取相关音频并返回（可能爬到奇奇怪怪的东西）
    #随机美图：从nekosapi随机获取一张“安全的”图片
    以#开头的指令无需@机器人也能生效
"""

# 采用的QQ机器人框架：LLBot 8.1.8
# 框架原地址：https://github.com/LLOneBot/LuckyLilliaBot（骗你的，不安装LLBot机器人是运行不了的）

# 从 Config.txt 读取配置
configPath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Config.txt")
if not os.path.exists(configPath):
    print("Config.txt 不存在，请创建并填写四行：BotQQ, LLM_API, LLM_KEY, LLM_MODEL")
    sys.exit(1)
with open(configPath, "r", encoding="utf-8") as f:
    lines = [line.strip() for line in f if line.strip()]
    if len(lines) < 4:
        print("Config.txt 至少需要四行：BotQQ, LLM_API, LLM_KEY, LLM_MODEL")
        sys.exit(1)
    botQQ = lines[0]
    llmApi = lines[1]
    llmKey = lines[2]
    llmModel = lines[3]

# LLBot启动后会在本机开放一个仅有本机可以访问的http服务器
# AutoReply通过端口3000与LLBot服务器进行交互，同时LLBot与QQ客户端进行更底层的交互并将结果转告给AutoReply
# 当然，在AutoReply运行过程中，LLBot服务器千万不能关闭，不然 我缺的服务这块谁给我补啊

OB_API = "http://127.0.0.1:3000"
SSE_HOST, SSE_PORT, SSE_PATH = "127.0.0.1", 3000, "/_events"
LLM_TIMEOUT = 60
MAX_TURNS = 50
MAX_LEN = 256
HIST_KEEP = 30
CTX_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "context")
DOWNLOAD_TIMEOUT = 20

# 对话提示词
# 至于为什么叫小鲸鱼...因为我最初测试的时候用的是DeepSeek的API
# 反正名字随你喜欢，随便改

SYSTEM_PROMPT = (
    "你是小鲸鱼 一只鲸鱼娘女仆 性格温柔活泼 说话平易近人 语气自然亲切\n"
    "说话方式紧凑简洁 尽量少用标点 不用多余空格和客套话\n"
    f"每次回复尽量不超过{MAX_LEN}个字 只输出纯文本 不要用markdown或代码块\n"
    "如果用户和你闲聊或提问 就轻松自然地回应 偶尔带点女仆式可爱"
)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 对话上下文会保存至本地JSON文件中

def ctxPath(key: str) -> str:
    return os.path.join(CTX_DIR, f"{key}.json")

def loadCtx(key: str) -> dict:
    p = ctxPath(key)
    if os.path.exists(p):
        try:
            with open(p, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"key": key, "turns": 0, "messages": []}

def saveCtx(ctx: dict):
    os.makedirs(CTX_DIR, exist_ok=True)
    with open(ctxPath(ctx["key"]), "w", encoding="utf-8") as f:
        json.dump(ctx, f, ensure_ascii=False, indent=1)

# 通过特定API指令与LLBot服务器进行交互
# API文档详见 https://luckylillia.com/guide/introduction

def postAction(action: str, payload: dict):
    timeout = 120 if action in ("upload_group_file", "upload_private_file") else 15
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{OB_API}/{action}", data=body,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        print(f"[{time.strftime('%H:%M:%S')}] 发送失败({action}): {e}", flush=True)
        return None

def sendText(targetType: str, targetId, content: str):
    if targetType == "group":
        return postAction("send_group_msg", {"group_id": targetId, "message": content})
    return postAction("send_private_msg", {"user_id": targetId, "message": content})

def sendFile(targetType: str, targetId, filePath: str, fileName: str = "") -> bool:
    name = fileName or Path(filePath).name
    if targetType == "group":
        resp = postAction("upload_group_file", {
            "group_id": targetId,
            "file": filePath,
            "name": name,
        })
    else:
        resp = postAction("upload_private_file", {
            "user_id": targetId,
            "file": filePath,
            "name": name,
        })
    try:
        return bool(resp) and json.loads(resp).get("status") == "ok"
    except Exception:
        return False

def extractText(msg) -> str:
    if isinstance(msg, str):
        return msg
    parts = []
    if isinstance(msg, list):
        for seg in msg:
            if seg.get("type") == "text":
                t = seg.get("data", {}).get("text", "")
                if t:
                    parts.append(t)
    return "".join(parts).strip()

def wasAtMe(msg) -> bool:
    if isinstance(msg, list):
        for seg in msg:
            if seg.get("type") == "at":
                qq = seg.get("data", {}).get("qq")
                if str(qq) == str(botQQ):
                    return True
    elif isinstance(msg, str) and f"@{botQQ}" in msg:
        return True
    return False

def askLLm(messages: list) -> str:
    body = json.dumps({
        "model": llmModel,
        "messages": messages,
        "max_tokens": 500,
        "temperature": 0.9,
    }).encode("utf-8")
    req = urllib.request.Request(
        llmApi, data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {llmKey}",
        },
    )
    with urllib.request.urlopen(req, timeout=LLM_TIMEOUT) as r:
        resp = json.loads(r.read().decode("utf-8", errors="replace"))
    return resp["choices"][0]["message"]["content"].strip()

# 点歌功能
# 1、调用BiliCatcher模块的下载功能下载音频到本地
# 2、调用LLBot文件上传API上传音频
# 3、清理本地音频文件
# 目前AutoReply是单线程SSE循环，一次只能处理一条信息，新消息（应该）是以消息队列的形式存放在LLBot中等待后续执行
# 因此不必担心并发时序问题——毕竟单步执行

def downloadSongAndReply(targetType: str, targetId, keyword: str):
    failMsg = f"未能成功获取{keyword}的歌曲资源"
    files = BiliCatcher.downloadSong(keyword)
    if not files:
        sendText(targetType, targetId, failMsg)
        return

    musicDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "TempMusic")
    if not os.path.isdir(musicDir):
        sendText(targetType, targetId, failMsg)
        return

    allFiles = sorted(f for f in os.listdir(musicDir) if f.lower().endswith(".m4a"))
    if not allFiles:
        sendText(targetType, targetId, failMsg)
        return

    failed = []
    for name in allFiles:
        path = os.path.join(musicDir, name)
        if sendFile(targetType, targetId, path):
            print(f"[{time.strftime('%H:%M:%S')}] 已发送文件: {name}", flush=True)
            try:
                os.remove(path)
            except OSError as e:
                print(f"[{time.strftime('%H:%M:%S')}] 清理失败 {path}: {e}", flush=True)
        else:
            failed.append(name)
            print(f"[{time.strftime('%H:%M:%S')}] 文件发送失败: {name}", flush=True)

    if failed:
        sendText(targetType, targetId, f"有 {len(failed)} 个文件发送失败: {'、'.join(failed)}")

# 原理与点歌功能相似
# 另外你可以去配置RndPic模块中的rating...懂的都懂（喜）

def handleRandomPic(targetType: str, targetId):
    failMsg = "获取随机美图失败"
    files = RndPic.fetchRandomPic()
    if not files:
        sendText(targetType, targetId, failMsg)
        return

    picDir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "TempPic")
    if not os.path.isdir(picDir):
        sendText(targetType, targetId, failMsg)
        return

    allFiles = sorted(os.listdir(picDir))
    if not allFiles:
        sendText(targetType, targetId, failMsg)
        return

    failed = []
    for name in allFiles:
        path = os.path.join(picDir, name)
        if sendFile(targetType, targetId, path):
            print(f"[{time.strftime('%H:%M:%S')}] 已发送文件: {name}", flush=True)
            try:
                os.remove(path)
            except OSError as e:
                print(f"[{time.strftime('%H:%M:%S')}] 清理失败 {path}: {e}", flush=True)
        else:
            failed.append(name)
            print(f"[{time.strftime('%H:%M:%S')}] 文件发送失败: {name}", flush=True)

    if failed:
        sendText(targetType, targetId, f"有 {len(failed)} 个文件发送失败: {'、'.join(failed)}")

def handleCommand(event: dict, mtype: str, text: str):
    if mtype == "group":
        targetType, targetId = "group", event.get("group_id")
        userId = event.get("user_id")
    else:
        targetType, targetId = "private", event.get("user_id")
        userId = targetId

    if text.startswith("#功能"):
        sendText(targetType, targetId, "1、#点歌 <关键字>\n2、#点赞\n3、#随机美图")
        return

    if text.startswith("#点歌"):
        keyword = text[len("#点歌"):].strip()
        if not keyword:
            sendText(targetType, targetId, "用法：#点歌 <关键字>")
            return
        sendText(targetType, targetId, f"正在获取《{keyword}》的歌曲资源，请稍候...")
        downloadSongAndReply(targetType, targetId, f"\"{keyword}\"")
        return

    if text.startswith("#点赞"):
        respStr = postAction("send_like", {"user_id": userId, "times": 10})
        if respStr:
            try:
                resp = json.loads(respStr)
                if resp.get("status") == "ok":
                    sendText(targetType, targetId, "已完成10次点赞")
                else:
                    sendText(targetType, targetId, f"点赞失败，错误信息：{resp}")
            except Exception:
                sendText(targetType, targetId, "点赞失败，未知错误")
        else:
            sendText(targetType, targetId, "点赞失败，无法连接服务器")
        return

    if text.startswith("#随机美图"):
        sendText(targetType, targetId, "正在获取随机美图（等级：SFW），请稍候...")
        handleRandomPic(targetType, targetId)
        return

    sendText(targetType, targetId, "未知指令，目前支持：\n#点歌 <关键字>\n#点赞\n#随机美图")

def handleEvent(event: dict):
    if event.get("post_type") != "message":
        return

    mtype = event.get("message_type")
    msg = event.get("message")
    text = extractText(msg)

    if not text:
        return

    if text.startswith("#"):
        handleCommand(event, mtype, text)
        return

    if mtype == "group":
        if not wasAtMe(msg):
            return
        targetId = event.get("group_id")
        action = "send_group_msg"
        payload = {"group_id": targetId, "message": None}
        key = f"group_{targetId}"
        label = f"群 {targetId}"
    elif mtype == "private":
        targetId = event.get("user_id")
        action = "send_private_msg"
        payload = {"user_id": targetId, "message": None}
        key = f"private_{targetId}"
        label = f"私聊 {targetId}"
    else:
        return

    ctx = loadCtx(key)

    if ctx["turns"] >= MAX_TURNS:
        ctx["messages"] = []
        ctx["turns"] = 0
        saveCtx(ctx)
        p = dict(payload)
        p["message"] = "本轮对话已结束，小鲸鱼已重置"
        postAction(action, p)
        print(f"[{time.strftime('%H:%M:%S')}] {label} 50轮用满 已重置", flush=True)

    ctx["turns"] += 1
    ctx["messages"].append({"role": "user", "content": text})

    apiMessages = [{"role": "system", "content": SYSTEM_PROMPT}]
    apiMessages += ctx["messages"][-HIST_KEEP:]

    try:
        reply = askLLm(apiMessages)
    except Exception as e:
        ctx["turns"] -= 1
        ctx["messages"].pop()
        saveCtx(ctx)
        print(f"[{time.strftime('%H:%M:%S')}] {label} AI请求失败: {e}", flush=True)
        return

    ctx["messages"].append({"role": "assistant", "content": reply})
    saveCtx(ctx)

    p = dict(payload)
    p["message"] = reply
    postAction(action, p)
    print(f"[{time.strftime('%H:%M:%S')}] {label} 轮{ctx['turns']} 回复 {len(reply)}字: {reply}", flush=True)

def sseLoop():
    s = socket.create_connection((SSE_HOST, SSE_PORT), timeout=30)
    s.settimeout(None)
    req = (
        f"GET {SSE_PATH} HTTP/1.1\r\n"
        f"Host: {SSE_HOST}:{SSE_PORT}\r\n"
        "Accept: text/event-stream\r\n"
        "Connection: keep-alive\r\n\r\n"
    )
    s.sendall(req.encode())
    f = s.makefile("rb", buffering=0)
    while True:
        line = f.readline()
        if not line or line == b"\r\n":
            break
    while True:
        line = f.readline()
        if not line:
            break
        text = line.decode("utf-8", errors="replace").rstrip("\r\n")
        if text.startswith("data:"):
            data = text[5:].strip()
            if not data:
                continue
            try:
                ev = json.loads(data)
                handleEvent(ev)
            except json.JSONDecodeError:
                pass
            except Exception as e:
                print(f"处理事件出错: {e}", flush=True)
    s.close()

def main():
    print("=== 小鲸鱼 AI 自动回复 启动 ===", flush=True)
    print(f"机器人: {botQQ} | 模型: {llmModel} | 上限: {MAX_TURNS}轮/{MAX_LEN}字 | 上下文: {CTX_DIR}", flush=True)
    while True:
        try:
            sseLoop()
        except Exception as e:
            print(f"SSE 连接断开: {e}，3 秒后重连...", flush=True)
            time.sleep(3)

if __name__ == "__main__":
    main()
