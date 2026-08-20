import os
import re
import json
import requests
from bs4 import BeautifulSoup

# 基于对B站网页结构逆向分析编写的爬虫
# 理论上走api.bilibili.com这样的官方API更好
# 但是嘛...按自己的想法来也不是不行（笑）

requestHeaders = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': '*/*',
    'Accept-Encoding': 'identity',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': 'https://www.bilibili.com/',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Sec-Fetch-Dest': 'video',
    'Sec-Fetch-Mode': 'no-cors',
    'Sec-Fetch-Site': 'cross-site'
}
session = requests.Session()
session.headers.update(requestHeaders)

# 视频播放界面地址存在于网页中的<a href>且其中不包含space标签的结构（space标签是主页）
# 视频标题存放在<img alt>中
# 每个视频播放界面地址都会在网页中重复出现一次（网页结构使然）
# 因此必须跳过重复计入的地址

def searchVideos(keyword):
    url = 'https://search.bilibili.com/all'
    params = {'keyword': keyword, 'search_source': '3'}
    resp = session.get(url, params=params)
    if resp.status_code != 200:
        return []
    soup = BeautifulSoup(resp.text, 'html.parser')
    hrefs = [a['href'] for a in soup.find_all('a', href=True) if 'space' not in a['href']]
    titles = [img['alt'] for img in soup.find_all('img', alt=True) if len(img['alt']) > 0]
    count = min(len(titles), len(hrefs) // 2)
    return [(titles[i], hrefs[i * 2]) for i in range(count)]

# 视频的视频*与音频数据流地址存放在视屏播放界面中window.__playinfo__关键字后的JSON中
# 通过['data']['dash']['audio']获取音频地址
# 通过['data']['dash']['video']获取视频地址
# *此处的“视频”是与音频信息完全分离的。B站将音频与“视频”（纯画面）分离以方便客户端的解析
# 我们此处仅抓取音频数据
# 另外JSON中存在baseUrl与backupUrl关键字，表示主地址/备用地址
# 且存在“mcdn”字样的域名下的服务器对会话的校验普遍宽松，因此优先选择

def getAudioUrl(playAddress):
    try:
        webpage = session.get(playAddress)
    except:
        return None
    if webpage.status_code != 200:
        return None
    match = re.search(r'window\.__playinfo__\s*=\s*({.*?})\s*</script>', webpage.text, re.DOTALL)
    if not match:
        return None
    data = json.loads(match.group(1))['data']['dash']['audio']
    for audio in data:
        for key in ('baseUrl', 'backupUrl'):
            if key in audio and 'mcdn' in audio[key]:
                return audio[key]
    return data[0]['baseUrl'] if data else None

def downloadAudio(audioUrl, savePath):
    resp = session.get(audioUrl, stream=True)
    resp.raise_for_status()
    with open(savePath, 'wb') as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)

def downloadSong(keyword):
    scriptDir = os.path.dirname(os.path.abspath(__file__))
    saveDir = os.path.join(scriptDir, 'TempMusic')
    os.makedirs(saveDir, exist_ok=True)
    videos = searchVideos(keyword)
    if not videos:
        return []
    title, playUrl = videos[0]
    audioUrl = getAudioUrl('https:' + playUrl)
    if not audioUrl:
        return []
    safeName = re.sub(r'[<>:"/\\|?*\x00-\x1f]', '', title).strip() or keyword
    path = os.path.join(saveDir, safeName + '.m4a')
    try:
        downloadAudio(audioUrl, path)
        return [path]
    except Exception:
        return []