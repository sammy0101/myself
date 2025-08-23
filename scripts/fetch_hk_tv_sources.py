# scripts/fetch_hk_tv_sources.py
import requests
import re
from bs4 import BeautifulSoup
import os
from datetime import datetime
import time

def fetch_hk_tv_sources():
    # 收集多个来源的香港电视直播源
    all_sources = []
    
    # 来源1: 从GitHub获取范明明的直播源
    try:
        print("正在从范明明源获取直播源...")
        response = requests.get("https://live.fanmingming.com/tv/m3u/ipv6.m3u", timeout=10)
        if response.status_code == 200:
            sources = parse_m3u_content(response.text, "范明明源")
            # 筛选出香港相关的频道
            hk_sources = [s for s in sources if "香港" in s["group"] or "HK" in s["name"].upper() or "TVB" in s["name"].upper()]
            all_sources.extend(hk_sources)
            print(f"从范明明源获取到 {len(hk_sources)} 个香港频道")
    except Exception as e:
        print(f"从范明明源获取失败: {e}")
    
    # 来源2: 从GitHub获取iptv-org的香港直播源
    try:
        print("正在从iptv-org获取香港直播源...")
        response = requests.get("https://iptv-org.github.io/iptv/countries/hk.m3u", timeout=10)
        if response.status_code == 200:
            sources = parse_m3u_content(response.text, "iptv-org")
            all_sources.extend(sources)
            print(f"从iptv-org获取到 {len(sources)} 个香港频道")
    except Exception as e:
        print(f"从iptv-org获取失败: {e}")
    
    # 来源3: 从epg.pw获取香港频道
    try:
        print("正在从epg.pw获取香港频道...")
        response = requests.get("https://epg.pw/test_channels_hong_kong.m3u", timeout=10)
        if response.status_code == 200:
            sources = parse_m3u_content(response.text, "epg.pw")
            all_sources.extend(sources)
            print(f"从epg.pw获取到 {len(sources)} 个香港频道")
    except Exception as e:
        print(f"从epg.pw获取失败: {e}")
    
    # 来源4: 从AKTV获取直播源
    try:
        print("正在从AKTV获取直播源...")
        response = requests.get("https://aktv.space/live.m3u", timeout=10)
        if response.status_code == 200:
            sources = parse_m3u_content(response.text, "AKTV")
            # 筛选出香港相关的频道
            hk_sources = [s for s in sources if "香港" in s["group"] or "HK" in s["name"].upper() or "TVB" in s["name"].upper()]
            all_sources.extend(hk_sources)
            print(f"从AKTV获取到 {len(hk_sources)} 个香港频道")
    except Exception as e:
        print(f"从AKTV获取失败: {e}")
    
    # 去重处理
    unique_sources = []
    seen_urls = set()
    for source in all_sources:
        if source["url"] not in seen_urls:
            unique_sources.append(source)
            seen_urls.add(source["url"])
    
    print(f"去重后共获取到 {len(unique_sources)} 个唯一香港频道")
    
    # 如果没有获取到任何源，使用备用源
    if not unique_sources:
        print("使用备用直播源...")
        unique_sources = [
            {"name": "TVB翡翠台", "url": "https://example.com/tvb1.m3u8", "group": "香港"},
            {"name": "TVB明珠台", "url": "https://example.com/tvb2.m3u8", "group": "香港"},
            {"name": "ViuTV", "url": "https://example.com/viutv.m3u8", "group": "香港"},
            {"name": "香港开电视", "url": "https://example.com/hkotv.m3u8", "group": "香港"},
            {"name": "RTHK31", "url": "https://example.com/rthk31.m3u8", "group": "香港"},
            {"name": "RTHK32", "url": "https://example.com/rthk32.m3u8", "group": "香港"}
        ]
    
    # 生成M3U文件
    generate_m3u(unique_sources)
    
    # 生成TXT文件
    generate_txt(unique_sources)
    
    print("香港电视直播源已更新")

def parse_m3u_content(m3u_content, source_name):
    """解析M3U内容并提取频道信息"""
    sources = []
    lines = m3u_content.split('\n')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line.startswith('#EXTINF:'):
            # 提取频道信息
            params = {}
            name = ""
            
            # 解析EXTINF行
            match = re.search(r'#EXTINF:-1\s*(.*),(.*)', line)
            if match:
                # 解析参数
                params_str = match.group(1)
                if params_str:
                    param_matches = re.findall(r'([^=]+)="([^"]*)"', params_str)
                    for key, value in param_matches:
                        params[key] = value
                
                # 获取频道名称
                name = match.group(2).strip()
            
            # 获取下一行的URL
            if i + 1 < len(lines):
                url = lines[i + 1].strip()
                if url and not url.startswith('#'):
                    group = params.get('group-title', source_name)
                    sources.append({
                        "name": name,
                        "url": url,
                        "group": group
                    })
                    i += 1  # 跳过URL行
        i += 1
    
    return sources

def generate_m3u(sources):
    m3u_content = "#EXTM3U\n"
    for source in sources:
        m3u_content += f'#EXTINF:-1 tvg-id="" tvg-name="{source["name"]}" tvg-logo="" group-title="{source["group"]}",{source["name"]}\n'
        m3u_content += f'{source["url"]}\n'
    
    with open("hk_tv_sources.m3u", "w", encoding="utf-8") as f:
        f.write(m3u_content)

def generate_txt(sources):
    txt_content = "# 香港电视直播源\n"
    txt_content += f"# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    txt_content += "# 此文件由GitHub Actions自动生成，每2天更新一次\n\n"
    
    for source in sources:
        txt_content += f"{source['name']},{source['url']}\n"
    
    with open("hk_tv_sources.txt", "w", encoding="utf-8") as f:
        f.write(txt_content)

if __name__ == "__main__":
    fetch_hk_tv_sources()
