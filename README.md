# 小鲸鱼 QQ 机器人

一个基于[OneBot](https://github.com/botuniverse/onebot)协议和大语言模型（LLM）API 的 QQ 自动回复机器人。

机器人的人设是一只名叫「小鲸鱼」的鲸鱼娘女仆，性格温柔活泼。它可以陪你聊天、帮你点歌、点赞、发随机美图，还能查天气、看新闻、把你的文字合成语音（活字印刷），所有命令以 `#` 开头，无需 @ 机器人也能生效。

> 本项目最初使用 DeepSeek 的 API 进行测试，所以人设名取了「小鲸鱼」。名字和人设都可以随意修改（见 `AutoReply.py` 中的 `SYSTEM_PROMPT`）。

---

## 功能特性

| 功能 | 触发方式 | 说明 |
| ---- | -------- | ---- |
| AI 对话 | 群聊中 `@机器人 <消息>` / 私聊直接发消息 | 调用 LLM 对话，每个群聊、私聊都视为独立会话 |
| 查看功能 | `#功能` | 列出当前支持的所有命令 |
| 点歌 | `#点歌 <关键字>` | 从 B 站搜索并下载相关音频，作为文件发送到聊天中 |
| 点赞 | `#点赞` | 给发送命令的用户 QQ 点赞 10 次 |
| 随机美图 | `#随机美图` | 从 nekosapi 随机获取一张「安全级」（SFW）图片并发送 |
| 天气 | `#天气 <城市名称>` | 从 wttr.in 获取城市天气图（PNG）并发送 |
| 新闻 | `#新闻 [日期]` | 获取「60秒看天下」新闻摘要，默认当天，可指定日期 |
| 活字印刷 | `#活字印刷 <文字>` | 将文字交给在线 TTS 服务合成语音，以语音消息（.ogg）发送 |

**对话特性：**

- 每个会话（群聊 / 私聊）独立保存上下文，最多保留 **50 轮**，用满后自动重置（会提示「本轮对话已结束，小鲸鱼已重置」）。
- 每次向 LLM 发送时只携带最近 **30 条**消息，避免超出模型上下文长度。
- 回复通过SYSTEM_PROMPT **软性**限制在 **256 字**以内，只输出纯文本，不使用 Markdown。

---

## 工作原理（以 LLBot 框架为例）

```
QQ 客户端
   ▲  │
   │  ▼
 LLBot 框架（本地 HTTP 服务器，端口 3000）
   ▲  │  SSE 事件推送（/_events）   HTTP API（send_group_msg 等）
   │  ▼
 AutoReply.py（本仓库主程序）
   │  ├─► LLM API（OpenAI 兼容的 Chat Completions 接口）── AI 对话
   │  ├─► BiliCatcher.py ──► 哔哩哔哩（点歌）
   │  ├─► RndPic.py ──────► nekosapi（随机美图）
   │  ├─► weather.py ─────► wttr.in（天气图）
   │  ├─► HZYSAPI.py ─────► ottohzys 在线 TTS（活字印刷语音）
   │  └─► 60s-static.viki.moe（新闻，直接请求）
```

- [LLBot](https://github.com/LLOneBot/LuckyLilliaBot)负责与 QQ 客户端进行底层交互，启动后会在本机 `127.0.0.1:3000` 开放一个仅本机可访问的 HTTP 服务器。
- ℹ️ 再次提醒，小鲸鱼实际上可以与**任意**支持[OneBot](https://github.com/botuniverse/onebot)协议的 QQ 消息框架配合使用。**本例程中仅采用 LLBot 框架进行演示**。该项目同样可以**根据实际需要迁移到其他通讯平台上**，比如微信与 Telegram。
- `AutoReply.py` 通过该服务器的 HTTP API 发送消息 / 点赞 / 上传文件，并通过 SSE（`/_events`）订阅新消息事件。
- **运行期间 LLBot（OneBot） 服务器绝对不能关闭**，否则机器人会失去与 QQ 的通信通道。SSE 连接意外断开时程序会自动在 3 秒后重连。
- 主程序是单线程的 SSE 循环，一次只处理一条消息，无需担心并发时序问题。
- 由于架构设计使然，小鲸鱼的信息吞吐量较小，仅适合作为个人项目**在较低并发要求的环境下使用**。

---

## 环境要求

- **Python 3.12+**（`weather.py` 中使用了同引号嵌套的 f-string 语法，仅 Python 3.12 及以上版本支持）
- [LuckyLilliaBot（LLBot）](https://github.com/LLOneBot/LuckyLilliaBot) v8.1.8（代码按此版本编写），以及一个登录状态的 QQ 客户端
- 一个 **符合 OpenAI API规范** 的 LLM API（智谱 GLM、DeepSeek、OpenAI 等均可）

### Python 依赖

```bash
pip install requests beautifulsoup4
```

其余功能均使用 Python 标准库（`json`、`socket`、`urllib`、`os`、`re` 等），无需额外安装。

---

## 安装与配置

### 0. 获取AutoReply脚本文件

请从 [Releases](https://github.com/Yauhak/AutoReply_LLBot/releases) 下载压缩包并解压到任意文件夹下。

### 1. 安装并启动 LLBot

1. 从 [LuckyLilliaBot Releases](https://github.com/LLOneBot/LuckyLilliaBot/releases) 下载 v8.1.8 并安装（Windows 用户可直接使用桌面版 / CLI 版）。
2. 登录你的 QQ 机器人账号。
3. 确认 LLBot 在本机 `3000` 端口开放了 HTTP 服务器（默认配置）。

### 2. 为 LLBot 配置 FFmpeg

LLBot 的语音发送功能必须配合 FFmpeg，否则小鲸鱼的活字印刷功能将无法使用。
请参阅 [相关文档](https://luckylillia.com/guide/ffmpeg) 进行 FFmpeg 配置。
若采用其他消息框架，请根据实际情况查询相应文档并进行正确配置。

### 3. 配置 `Config.txt`

在项目根目录创建（或修改）`Config.txt`，**共四行，每行一项，顺序固定**：

```text
BotQQ
LLM_API
LLM_KEY
LLM_MODEL
```

| 行号 | 配置项 | 示例 | 说明 |
| ---- | ------ | ---- | ---- |
| 1 | 机器人 QQ 号 | `1234567890` | 用于判断消息是否 @ 了机器人 |
| 2 | LLM API 地址 | `https://open.bigmodel.cn/api/paas/v4/chat/completions` | 智谱GLM Chat Completions 接口 |
| 3 | API 密钥 | `sk-xxxx...` | 对应平台的 API Key |
| 4 | 模型名称 | `glm-4.5-flash` | 模型 ID，取决于你使用的平台 |

配置示例（以智谱 GLM 为例）：

```text
1234567890
https://open.bigmodel.cn/api/paas/v4/chat/completions
你的API密钥
glm-4.5-flash
```

> ⚠️ **注意**：`Config.txt` 包含你的 API 密钥，请勿提交到 Git 仓库或分享给他人。

### 4. 启动机器人

```bash
python AutoReply.py
```

启动后终端会显示机器人 QQ 号、模型名称、轮数上限和上下文目录，随后开始监听消息。

---

## 使用说明

### 对话

- **群聊**：必须 `@机器人` 才会回复（`@` 与消息之间可以有其他文字）。
- **私聊**：直接发送消息即可对话。
- 每条消息会被记录到对应会话的上下文中，回复由 LLM 生成。

### 命令（以 `#` 开头，无需 @ 机器人）

```
#功能                    查看功能列表
#点歌 <关键字>            从B站搜索并下载音频，发送到当前聊天
#点赞                    给命令发送者点10个赞
#随机美图                获取一张随机美图（SFW等级）
#天气 <城市名称>          获取该城市的天气图
#新闻 [日期]             获取60秒新闻摘要（日期格式 YYYY-MM-DD，默认当天）
#活字印刷 <文字>          将文字合成语音并作为语音消息发送
```

示例：

```
#点歌 晴天
#点歌 周杰伦 七里香
#随机美图
#点赞
#天气 北京
#新闻
#新闻 2026-08-19
#活字印刷 大家好啊，我是说的道理
```

输入不认识的命令时，机器人会回复当前支持的命令列表。

---

## 文件结构

```
E:\QQBot\
├── AutoReply.py        # 主程序：SSE 事件循环、指令分发、LLM 对话、文件上传
├── BiliCatcher.py      # B 站爬虫模块：搜索视频、提取并下载音频（点歌功能）
├── RndPic.py           # 随机图片模块：调用 nekosapi 下载图片（随机美图功能）
├── weather.py          # 天气模块：调用 wttr.in 下载天气图片（天气功能）
├── HZYSAPI.py          # 活字印刷模块：调用在线 TTS 服务合成语音（活字印刷功能）
├── Config.txt          # 配置文件：BotQQ / LLM_API / LLM_KEY / LLM_MODEL（勿外泄！）
├── context\            # 会话上下文 JSON（*自动创建，每个会话一个文件）
├── TempMusic\          # 点歌下载的临时音频目录（*自动创建，发送成功后自动删除）
├── TempPic\            # 随机美图下载的临时图片目录（*自动创建，发送成功后自动删除）
├── Weather\            # 天气图片临时目录（*自动创建，发送成功后自动删除）
└── HZYS\               # 活字印刷语音临时目录（*自动创建，发送成功后自动删除）
```

---

## 模块说明

### AutoReply.py — 主程序

- 读取 `Config.txt` 配置；不存在或不足四行时会提示并退出。
- 通过 `postAction()` 调用 LLBot 的 HTTP API（如 `send_group_msg`、`send_private_msg`、`upload_group_file`、`send_like`）。
- 通过 SSE 长连接（`127.0.0.1:3000/_events`）订阅消息事件，断线自动重连。
- 会话上下文以 JSON 形式保存在 `context\` 目录，键名为 `group_<群号>` / `private_<QQ号>`。
- 统一通过 `handlePic()` 处理「随机美图」与「天气」两类图片：下载 → 上传文件 → 清理本地文件。
- 「活字印刷」生成语音后，通过 `record` 消息段（`file://` 路径）以语音消息发送，发送成功后清理 `HZYS\` 目录。
- 对话人设、字数上限、轮数上限、上下文保留条数等均可直接在文件顶部的常量区修改：

| 常量 | 默认值 | 含义 |
| ---- | ------ | ---- |
| `SYSTEM_PROMPT` | 小鲸鱼人设 | 系统提示词，决定机器人性格 |
| `MAX_TURNS` | 50 | 每会话最大轮数，用满自动重置 |
| `MAX_LEN` | 256 | 单次回复最大字数（写入人设提示词） |
| `HIST_KEEP` | 30 | 每次请求携带的最近消息条数 |
| `LLM_TIMEOUT` | 60 | LLM 请求超时（秒） |

### BiliCatcher.py — 点歌

- 基于对 B 站网页结构的逆向分析实现的爬虫，并未使用官方 API，因此 B 站改版后可能需要维护。
- `searchVideos()`：在 `search.bilibili.com` 搜索，解析页面中的视频链接与标题（跳过含 `space` 的链接，并去重）。
- `getAudioUrl()`：从视频播放页的 `window.__playinfo__` JSON 中提取 DASH 音频流地址，优先选择 `mcdn` 域名（校验宽松）。
- `downloadSong()`：下载第一个搜索结果的音频，保存为 `TempMusic\<标题>.m4a`。

### RndPic.py — 随机美图

- 调用 `https://api.nekosapi.com/v4/images/random` 获取随机图片并下载到 `TempPic\`。
- `rating` 参数控制内容分级：`safe`（默认）、`suggestive`、`borderline`、`explicit`。
- ⚠️ **警告**：该 API 网站上成人内容非常多，即使是 `safe` 等级也可能出现「惊喜」，请谨慎使用与修改分级。

### weather.py — 天气

- 调用 `https://v3.wttr.in/<城市>.png` 获取天气图片（[wttr.in](https://wttr.in) 服务），下载到 `Weather\` 后由主程序作为文件发送。
- 城市名中的空格会被替换为 `+`。
- 成功返回 `1`，失败返回 `0`，由主程序统一判断并提示。

### HZYSAPI.py — 活字印刷

- 将文字以表单形式 POST 到 `https://ottohzys.wzq02.top/make`（在线活字印刷 TTS 服务），获取音频 ID 后下载 `https://ottohzys.wzq02.top/get/<id>.ogg` 到 `HZYS\`。
- 可调参数：`inYsddMode`（原声大碟模式）、`norm`（统一音量）、`reverse`（倒放）、`speedMult`（速度倍率）、`pitchMult`（音调倍率），主程序目前使用默认值。
- 请求过于频繁会返回 429（「请求过多，请稍后再试（憋刷辣！）」）；该服务为第三方，接口可能随时变化。

---

## 常见问题

| 问题 | 解决方法 |
| ---- | -------- |
| 启动提示 `Config.txt 不存在` / `至少需要四行` | 按上文格式创建 / 补全 `Config.txt` |
| 消息无响应 | 检查 LLBot 是否在运行、3000 端口是否被占用，确认群聊中使用了 `@机器人` |
| 终端提示 `SSE 连接断开` | 程序会自动重连；若持续失败，检查 LLBot 状态 |
| `#点歌` 失败 | 可能是 B 站页面结构变化或网络问题，稍后再试；部分视频可能没有可用音频流 |
| `#随机美图` 失败 | 网络问题或 nekosapi 服务不可用 |
| `#天气` 失败 | wttr.in 服务不稳定或城市名无法识别，稍后再试或改用更标准的城市名 |
| `#新闻` 失败 | 60s 新闻 API 数据最早只覆盖近两年且存在数据空白，可按 `#新闻 YYYY-MM-DD` 格式重试 |
| `#活字印刷` 失败 / 提示请求过多 | 服务限流（429），稍等片刻再试；文字过长也可能导致生成失败 |
| 中文乱码 | 程序已强制使用 UTF-8 输出；Windows 终端请使用支持 UTF-8 的终端（如 Windows Terminal） |

---

## 安全提示

- `Config.txt` 中的 API 密钥属于敏感信息，**不要**提交到公开仓库或发送给他人；若已泄露请及时到对应平台重置。
- 本项目依赖的第三方服务（B 站爬虫、nekosapi、wttr.in、60s 新闻、活字印刷 TTS）均为非官方接口，使用请遵守其服务条款，并自行承担风险。

---

## 参考链接

- [LuckyLilliaBot（LLBot）框架仓库](https://github.com/LLOneBot/LuckyLilliaBot)
- [LLBot API 文档](https://luckylillia.com/guide/introduction)
- [OneBot协议](https://github.com/botuniverse/onebot)
- [配置 FFmpeg](https://luckylillia.com/guide/ffmpeg)
- [nekosapi 随机图片 API](https://nekosapi.com)
- [wttr.in 天气服务](https://wttr.in)
- [60s 新闻 API](https://60s-static.viki.moe/60s/)
- [活字印刷 TTS 服务](https://ottohzys.wzq02.top)
