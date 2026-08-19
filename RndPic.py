import os
import requests

# 基于nekosapi的随机图片获取功能
# 该API貌似最初就是为了给TG等聊天软件Bot提供随机图片服务而生的
# rating里可以改工作/年龄分级：safe、suggestive、borderline、explicit
# 悄咪咪提醒一句：这个API网站上的黄图非常多
# 哪怕是safe等级都可能爆出来“惊喜”

def fetchRandomPic():
    apiUrl = "https://api.nekosapi.com/v4/images/random"
    params = {"rating": "safe"}
    scriptDir = os.path.dirname(os.path.abspath(__file__))
    downloadDir = os.path.join(scriptDir, "TempPic")
    os.makedirs(downloadDir, exist_ok=True)
    try:
        resp = requests.get(apiUrl, params=params)
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.RequestException:
        return []
    if not data:
        return []
    first = data[0]
    imgUrl = first.get("url")
    if not imgUrl:
        return []
    try:
        imgResp = requests.get(imgUrl)
        imgResp.raise_for_status()
        filename = os.path.basename(imgUrl.split("?")[0])
        if not filename:
            filename = f"nekos_{first.get('id', 'unknown')}.webp"
        path = os.path.join(downloadDir, filename)
        with open(path, "wb") as f:
            f.write(imgResp.content)
        return [path]
    except requests.exceptions.RequestException:
        return []