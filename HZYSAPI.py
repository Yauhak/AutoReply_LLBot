import requests
import json
import os

# 依旧扒网页源代码
# 依旧逆向工程
# 依旧将核心数据处理过程丢给目标网站的后端以减小本地开销
# 依旧薅羊毛（bushi）

def convertTextToSound(text, inYsddMode=True, norm=False, reverse=False, speedMult=1, pitchMult=1):
    domain = "https://ottohzys.wzq02.top"
    scriptDir = os.path.dirname(os.path.abspath(__file__))
    downloadDir = os.path.join(scriptDir, "HZYS")
    os.makedirs(downloadDir, exist_ok=True)
    # 构造POST请求的URL
    url = domain + "/make"
    payload = {
        # 需要活字印刷的文本
        # 是否开启原声大碟模式
        # 是否统一音量
        # 是否倒放
        # 速度
        # 音调
        "text": text,
        "inYsddMode": str(inYsddMode).lower(),
        "norm": str(norm).lower(),
        "reverse": str(reverse).lower(),
        "speedMult": str(speedMult),
        "pitchMult": str(pitchMult)
    }

    response = requests.post(url, data=payload, headers={"Content-Type": "application/x-www-form-urlencoded"})
    if response.status_code == 200:
        try:
            data = response.json()
        except json.JSONDecodeError:
            raise RuntimeError("服务器返回非JSON格式数据")
        if "id" not in data:
            raise RuntimeError("响应中缺少音频ID")
        audio_id = data["id"]
        audio_url = f"{domain}/get/{audio_id}.ogg"

        try:
            audio = requests.get(audio_url)
            audio.raise_for_status()
            path = os.path.join(downloadDir, f"{audio_id}.ogg")
            with open(path, "wb") as f:
                f.write(audio.content)
            print(f"成功下载活字印刷音频：{path}")
            return path
        except Exception as e:
            print(f"活字印刷音频下载失败：{e}")
            return None

    elif response.status_code == 429:
        raise RuntimeError("请求过多，请稍后再试（憋刷辣！）")
    else:
        try:
            error_msg = response.json().get("message", "未知错误")
        except:
            error_msg = response.text or "未知错误"
        raise RuntimeError(f"服务器错误（状态码 {response.status_code}）: {error_msg}")
