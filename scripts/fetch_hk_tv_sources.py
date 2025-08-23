# scripts/fetch_hk_tv_sources.py
import requests
import re
from bs4 import BeautifulSoup
import os
from datetime import datetime

def fetch_hk_tv_sources():
    # 这里是一些示例的香港电视台直播源
    # 实际使用时，您需要替换为真实的获取直播源的逻辑
    tv_sources = [
        {"name": "TVB翡翠台", "url": "https://example.com/tvb1.m3u8", "group": "香港"},
        {"name": "TVB明珠台", "url": "https://example.com/tvb2.m3u8", "group": "香港"},
        {"name": "ViuTV", "url": "https://example.com/viutv.m3u8", "group": "香港"},
        {"name": "香港开电视", "url": "https://example.com/hkotv.m3u8", "group": "香港"},
        {"name": "RTHK31", "url": "https://example.com/rthk31.m3u8", "group": "香港"},
        {"name": "RTHK32", "url": "https://example.com/rthk32.m3u8", "group": "香港"}
    ]
    
    # 生成M3U文件
    generate_m3u(tv_sources)
    
    # 生成TXT文件
    generate_txt(tv_sources)
    
    print("香港电视直播源已更新")

def generate_m3u(sources):
    m3u_content = "#EXTM3U\n"
    for source in sources:
        m3u_content += f'#EXTINF:-1 group-title="{source["group"]}",{source["name"]}\n'
        m3u_content += f'{source["url"]}\n'
    
    with open("hk_tv_sources.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)

def generate_txt(sources):
    txt_content = "# 香港电视直播源\n"
    txt_content += f"# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    for source in sources:
        txt_content += f"{source['name']},{source['url']}\n"
    
    with open("hk_tv_sources.txt", "w", encoding="utf-8") as f:
        f.write(txt_content)

if __name__ == "__main__":
    fetch_hk_tv_sources()
