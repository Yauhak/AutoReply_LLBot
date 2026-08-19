# 小鲸鱼 QQ 机器人（AutoReply）

一个基于 [LuckyLilliaBot（LLBot）](https://github.com/LLOneBot/LuckyLilliaBot) 框架和大语言模型（LLM）API 的 QQ 自动回复机器人。

机器人的人设是一只名叫「小鲸鱼」的鲸鱼娘女仆，性格温柔活泼。它可以陪你聊天、帮你点歌、点赞、发随机美图，所有命令以 `#` 开头，无需 @ 机器人也能生效。

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

**对话特性：**

- 每个会话（群聊 / 私聊）独立保存上下文，最多保留 **50 轮**，用满后自动重置（会提示「本轮对话已结束，小鲸鱼已重置」）。
- 每次向 LLM 发送时只携带最近 **30 条**消息，避免超出模型上下文长度。
- 回复限制在 **256 字**以内，只输出纯文本，不使用 Markdown。

---

## 工作原理

```
QQ 客户端
   ▲  │
   │  ▼
 LLBot 框架（本地 HTTP 服务器，端口 3000）
   ▲  │  SSE 事件推送（/_events）   HTTP API（send_group_msg 等）
   │  ▼
 AutoReply.py（本仓库主程序）
   │  ├─► LLM API（OpenAI 兼容的 Chat Completions 接口）
   │  ├─► BiliCatcher.py ──► 哔哩哔哩（点歌）
   │  └─► RndPic.py ──────► nekosapi（随机美图）
```

- [LLBot](https://github.com/LLOneBot/LuckyLilliaBot) 负责与 QQ 客户端进行底层交互，启动后会在本机 `127.0.0.1:3000` 开放一个仅本机可访问的 HTTP 服务器。
- `AutoReply.py` 通过该服务器的 HTTP API 发送消息 / 点赞 / 上传文件，并通过 SSE（`/_events`）订阅新消息事件。
- **运行期间 LLBot 服务器绝对不能关闭**，否则机器人会失去与 QQ 的通信通道。SSE 连接意外断开时程序会自动在 3 秒后重连。
- 主程序是单线程的 SSE 循环，一次只处理一条消息，无需担心并发时序问题。

---

## 环境要求

- Python 3.8+（代码使用 `sys.stdout.reconfigure` 等特性，推荐 Python 3.8 以上）
- [LuckyLilliaBot（LLBot）](https://github.com/LLOneBot/LuckyLilliaBot) v8.1.8（代码按此版本编写），以及一个登录状态的 QQ 客户端
- 一个 **OpenAI 兼容** 的 LLM API（智谱 GLM、DeepSeek、OpenAI 等均可）

### Python 依赖

```bash
pip install requests beautifulsoup4
```

其余功能均使用 Python 标准库（`json`、`socket`、`urllib`、`os`、`re` 等），无需额外安装。

---

## 安装与配置

### 1. 安装并启动 LLBot

1. 从 [LuckyLilliaBot Releases](https://github.com/LLOneBot/LuckyLilliaBot/releases) 下载 v8.1.8 并安装（Windows 用户可直接使用桌面版 / CLI 版）。
2. 登录你的 QQ 机器人账号。
3. 确认 LLBot 在本机 `3000` 端口开放了 HTTP 服务器（默认配置）。

### 2. 配置 `Config.txt`

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
| 2 | LLM API 地址 | `https://open.bigmodel.cn/api/paas/v4/chat/completions` | 智谱GLM的 Chat Completions 接口 |
| 3 | API 密钥 | `sk-xxxx...` | 对应平台的 API Key |
| 4 | 模型名称 | `glm-4-flash` | 模型 ID，取决于你使用的平台 |

配置示例（以智谱 GLM 为例）：

```text
3948098306
https://open.bigmodel.cn/api/paas/v4/chat/completions
你的API密钥
glm-4-flash
```

> ⚠️ **注意**：`Config.txt` 包含你的 API 密钥，请勿提交到 Git 仓库或分享给他人。建议将其加入 `.gitignore`。

### 3. 启动机器人

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
#功能                 查看功能列表
#点歌 <关键字>         从B站搜索并下载音频，发送到当前聊天
#点赞                 给命令发送者点10个赞
#随机美图             获取一张随机美图（SFW等级）
```

示例：

```
#点歌 晴天
#点歌 周杰伦 七里香
#随机美图
#点赞
```

输入不认识的命令时，机器人会回复当前支持的命令列表。

---

## 文件结构

```
E:\QQBot\
├── AutoReply.py        # 主程序：SSE 事件循环、指令分发、LLM 对话、文件上传
├── BiliCatcher.py      # B 站爬虫模块：搜索视频、提取并下载音频（点歌功能）
├── RndPic.py           # 随机图片模块：调用 nekosapi 下载图片（随机美图功能）
├── Config.txt          # 配置文件：BotQQ / LLM_API / LLM_KEY / LLM_MODEL（勿外泄！）
├── context\            # 会话上下文 JSON（自动创建，每个会话一个文件）
├── TempMusic\          # 点歌下载的临时音频（发送成功后自动删除）
└── TempPic\            # 随机美图下载的临时图片（发送成功后自动删除）
```

---

## 模块说明

### AutoReply.py — 主程序

- 读取 `Config.txt` 配置；不存在或不足四行时会提示并退出。
- 通过 `postAction()` 调用 LLBot 的 HTTP API（如 `send_group_msg`、`send_private_msg`、`upload_group_file`、`send_like`）。
- 通过 SSE 长连接（`127.0.0.1:3000/_events`）订阅消息事件，断线自动重连。
- 会话上下文以 JSON 形式保存在 `context\` 目录，键名为 `group_<群号>` / `private_<QQ号>`。
- 对话人设、字数上限、轮数上限、上下文保留条数等均可直接在文件顶部的常量区修改：

| 常量 | 默认值 | 含义 |
| ---- | ------ | ---- |
| `SYSTEM_PROMPT` | 小鲸鱼人设 | 系统提示词，决定机器人性格 |
| `MAX_TURNS` | 50 | 每会话最大轮数，用满自动重置 |
| `MAX_LEN` | 256 | 单次回复最大字数（写入人设提示词） |
| `HIST_KEEP` | 30 | 每次请求携带的最近消息条数 |
| `LLM_TIMEOUT` | 60 | LLM 请求超时（秒） |

### BiliCatcher.py — 点歌

- 基于对 B 站网页结构的逆向分析实现的爬虫（作者自称「按自己的想法来」），并未使用官方 API，因此 B 站改版后可能需要维护。
- `searchVideos()`：在 `search.bilibili.com` 搜索，解析页面中的视频链接与标题（跳过含 `space` 的链接，并去重）。
- `getAudioUrl()`：从视频播放页的 `window.__playinfo__` JSON 中提取 DASH 音频流地址，优先选择 `mcdn` 域名（校验宽松）。
- `downloadSong()`：下载第一个搜索结果的音频，保存为 `TempMusic\<标题>.m4a`。

### RndPic.py — 随机美图

- 调用 `https://api.nekosapi.com/v4/images/random` 获取随机图片并下载到 `TempPic\`。
- `rating` 参数控制内容分级：`safe`（默认）、`suggestive`、`borderline`、`explicit`。
- ⚠️ **警告**：该 API 网站上成人内容非常多，即使是 `safe` 等级也可能出现「惊喜」，请谨慎使用与修改分级。

---

## 常见问题

| 问题 | 解决方法 |
| ---- | -------- |
| 启动提示 `Config.txt 不存在` / `至少需要四行` | 按上文格式创建 / 补全 `Config.txt` |
| 消息无响应 | 检查 LLBot 是否在运行、3000 端口是否被占用，确认群聊中使用了 `@机器人` |
| 终端提示 `SSE 连接断开` | 程序会自动重连；若持续失败，检查 LLBot 状态 |
| `#点歌` 失败 | 可能是 B 站页面结构变化或网络问题，稍后再试；部分视频可能没有可用音频流 |
| `#随机美图` 失败 | 网络问题或 nekosapi 服务不可用 |
| 中文乱码 | 程序已强制使用 UTF-8 输出；Windows 终端请使用支持 UTF-8 的终端（如 Windows Terminal） |

---

## 安全提示

- `Config.txt` 中的 API 密钥属于敏感信息，**不要**提交到公开仓库或发送给他人；若已泄露请及时到对应平台重置。
- 本项目的爬虫（B 站）与图片接口（nekosapi）均为第三方服务，使用请遵守其服务条款，并自行承担风险。

---

## 参考链接

- [LuckyLilliaBot（LLBot）框架仓库](https://github.com/LLOneBot/LuckyLilliaBot)
- [LLBot API 文档](https://luckylillia.com/guide/introduction)
- [nekosapi 随机图片 API](https://nekosapi.com)
