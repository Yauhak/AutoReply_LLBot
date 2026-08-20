import requests
import os

def getWeatherByCity(city):
    scriptDir = os.path.dirname(os.path.abspath(__file__))
    downloadDir = os.path.join(scriptDir, "Weather")
    os.makedirs(downloadDir, exist_ok=True)
    try:
        weatherImg = requests.get(f'https://v3.wttr.in/{city.replace(' ', '+')}.png')
        weatherImg.raise_for_status()
        path = os.path.join(downloadDir, f"{city.replace(' ', '+')}.png")
        with open(path, "wb") as f:
            f.write(weatherImg.content)
        print(f"成功获取 {city} 的天气")
        return 1
    except Exception as e:
        print(f"获取天气失败：{e}")
        return 0