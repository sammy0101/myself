# scripts/fetch_hk_tv_sources.py
import requests
import re
import time
import json
import os
import socket
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, parse_qs

class HKTVSourceFetcher:
    def __init__(self):
        self.sources = []
        self.timeout = 10
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # 定義分類優先級順序
        self.category_order = [
            'TVB', 'ViuTV', 'HOY TV', 'RTHK', '新聞', '體育', '電影', '國際', '兒童', '其他'
        ]
        # 更精確的頻道分類映射
        self.channel_categories = {
            # TVB頻道
            'TVB': ['TVB', '無綫', '翡翠', '明珠', 'J2', 'J5', '無綫新聞', '無綫財經', '無綫綜藝'],
            # ViuTV頻道
            'ViuTV': ['ViuTV', 'Viu', 'VIU'],
            # HOY TV頻道 (前開電視)
            'HOY TV': ['HOY', '開電視', '有線', '奇妙', '77台', '78台', '79台'],
            # RTHK頻道
            'RTHK': ['RTHK', '香港電台', '港台'],
            # 新聞頻道
            '新聞': ['新聞', 'NEWS', '資訊', '財經', 'INFO', '財經資訊'],
            # 體育頻道
            '體育': ['體育', 'SPORTS', '賽馬', '足球', '籃球', '運動'],
            # 電影頻道
            '電影': ['電影', 'MOVIE', '影院', '戲劇', 'CINEMA'],
            # 國際頻道
            '國際': ['國際', 'WORLD', 'BBC', 'CNN', 'NHK', 'DW', '鳳凰衛視'],
            # 兒童頻道
            '兒童': ['兒童', 'KIDS', '卡通', '動畫'],
        }
        # 語言映射
        self.language_map = {
            '粵語': ['粵語', 'CANTONESE', '廣東話'],
            '普通話': ['普通話', 'MANDARIN', '國語'],
            '英語': ['英語', 'ENGLISH'],
            '多語言': ['雙語', '多語', 'BILINGUAL']
        }
        # 頻道名稱標準化映射
        self.channel_name_mapping = {
            # TVB頻道
            r'.*翡翠台.*': 'TVB翡翠台',
            r'.*明珠台.*': 'TVB明珠台',
            r'.*J2.*': 'TVB J2',
            r'.*無綫新聞.*': 'TVB無綫新聞台',
            r'.*無綫財經.*': 'TVB無綫財經台',
            r'.*無綫綜藝.*': 'TVB無綫綜藝台',
            # ViuTV頻道
            r'.*ViuTV.*': 'ViuTV',
            r'.*VIU TV.*': 'ViuTV',
            # HOY TV頻道
            r'.*HOY TV.*': 'HOY TV',
            r'.*開電視.*': 'HOY TV',
            r'.*有線新聞.*': 'HOY新聞台',
            r'.*有線財經.*': 'HOY財經台',
            r'.*有線直播.*': 'HOY直播台',
            r'.*奇妙77.*': 'HOY TV',
            r'.*奇妙78.*': 'HOY資訊台',
            r'.*奇妙79.*': 'HOY國際財經台',
            # RTHK頻道
            r'.*RTHK.*31.*': 'RTHK 31',
            r'.*RTHK.*32.*': 'RTHK 32',
            r'.*香港電台.*31.*': 'RTHK 31',
            r'.*香港電台.*32.*': 'RTHK 32',
            # 新聞頻道
            r'.*鳳凰衛視.*中文台.*': '鳳凰衛視中文台',
            r'.*鳳凰衛視.*資訊台.*': '鳳凰衛視資訊台',
            r'.*鳳凰衛視.*香港台.*': '鳳凰衛視香港台',
            r'.*BBC.*': 'BBC新聞台',
            r'.*CNN.*': 'CNN新聞台',
            r'.*NHK.*': 'NHK世界台',
            # 體育頻道
            r'.*體育.*': '體育頻道',
            r'.*賽馬.*': '賽馬頻道',
            r'.*足球.*': '足球頻道',
        }
    
    def fetch_all_sources(self):
        """從所有可用來源獲取直播源"""
        print("開始獲取香港電視直播源...")
        
        # 定義所有來源
        sources_methods = [
            self.fetch_fanmingming_ipv6,
            self.fetch_fanmingming_v6,
            self.fetch_iptv_org_hk,
            self.fetch_epg_pw_hk,
            self.fetch_aktv,
            self.fetch_yuechan,
            self.fetch_bigbiggrandg,
        ]
        
        # 使用多線程並行獲取
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_method = {executor.submit(method): method.__name__ for method in sources_methods}
            
            for future in as_completed(future_to_method):
                method_name = future_to_method[future]
                try:
                    result = future.result()
                    print(f"{method_name} 完成")
                except Exception as e:
                    print(f"{method_name} 出錯: {e}")
        
        # 去重處理
        unique_sources = self.remove_duplicates()
        
        # 分類和增強元數據
        enhanced_sources = self.enhance_metadata(unique_sources)
        
        print(f"總共獲取到 {len(enhanced_sources)} 個香港頻道")
        
        # 測試連接並過濾無效源
        tested_sources = self.test_sources_connectivity(enhanced_sources)
        
        print(f"連接測試後剩餘 {len(tested_sources)} 個有效頻道")
        
        # 生成輸出文件
        self.generate_output_files(tested_sources)
        
        # 生成API文件
        self.generate_api_files(tested_sources)
        
        return tested_sources
    
    def test_sources_connectivity(self, sources):
        """測試源的連接性並過濾無效源"""
        print("開始測試頻道連接性...")
        
        valid_sources = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            # 創建測試任務
            future_to_source = {
                executor.submit(self.test_source_connectivity, source): source 
                for source in sources
            }
            
            # 處理結果
            for i, future in enumerate(as_completed(future_to_source)):
                source = future_to_source[future]
                try:
                    is_valid, response_time = future.result()
                    if is_valid:
                        source['response_time'] = response_time
                        valid_sources.append(source)
                        print(f"✓ {source['name']} - {response_time}ms")
                    else:
                        print(f"✗ {source['name']} - 無效")
                except Exception as e:
                    print(f"✗ {source['name']} - 測試錯誤: {e}")
                
                # 每測試10個源顯示一次進度
                if (i + 1) % 10 == 0:
                    print(f"已測試 {i + 1}/{len(sources)} 個頻道")
        
        return valid_sources
    
    def test_source_connectivity(self, source):
        """測試單個源的連接性"""
        url = source['url']
        
        # 跳過明顯無效的URL
        if not url or url.startswith('http://example.com'):
            return False, 9999
        
        try:
            # 解析主機名和端口
            parsed_url = urlparse(url)
            hostname = parsed_url.hostname
            port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
            
            # 首先測試TCP連接
            start_time = time.time()
            with socket.create_connection((hostname, port), timeout=5):
                tcp_time = int((time.time() - start_time) * 1000)
            
            # 然後測試HTTP請求
            start_time = time.time()
            response = requests.head(
                url, 
                timeout=5, 
                headers=self.headers,
                allow_redirects=True
            )
            http_time = int((time.time() - start_time) * 1000)
            
            # 計算總時間
            total_time = (tcp_time + http_time) // 2
            
            # 檢查響應狀態
            if response.status_code < 400:
                return True, total_time
            else:
                return False, total_time
                
        except (requests.RequestException, socket.timeout, socket.gaierror, OSError):
            return False, 9999
    
    def enhance_metadata(self, sources):
        """增強頻道元數據：分類、語言、清晰度等"""
        enhanced_sources = []
        
        for source in sources:
            # 標準化頻道名稱
            source['name'] = self.normalize_channel_name(source['name'])
            
            # 確定頻道分類 - 使用更精確的分類方法
            category = self.determine_category_precise(source['name'], source.get('group', ''))
            source['category'] = category
            
            # 確定語言
            language = self.determine_language(source['name'], source.get('group', ''))
            source['language'] = language
            
            # 確定清晰度
            resolution = self.determine_resolution(source['name'], source['url'])
            source['resolution'] = resolution
            
            # 確定是否高清
            source['hd'] = '高清' in source['name'] or 'HD' in source['name'].upper() or resolution in ['1080p', '720p']
            
            # 提取頻道ID/編號
            channel_id = self.extract_channel_id(source['name'])
            source['channel_id'] = channel_id
            
            enhanced_sources.append(source)
        
        return enhanced_sources
    
    def normalize_channel_name(self, name):
        """標準化頻道名稱"""
        # 去除多餘空格和特殊字符
        name = re.sub(r'\s+', ' ', name.strip())
        
        # 應用名稱映射
        for pattern, replacement in self.channel_name_mapping.items():
            if re.match(pattern, name, re.IGNORECASE):
                return replacement
        
        # 如果沒有匹配的映射，返回原始名稱（但清理過）
        return name
    
    def determine_category_precise(self, name, group):
        """更精確地確定頻道分類"""
        name_upper = name.upper()
        group_upper = group.upper()
        
        # 首先檢查特定頻道
        if any(keyword in name_upper for keyword in ['TVB', '無綫', '翡翠', '明珠', 'J2']):
            return 'TVB'
        elif any(keyword in name_upper for keyword in ['VIUTV', 'VIU TV']):
            return 'ViuTV'
        elif any(keyword in name_upper for keyword in ['HOY', '開電視', '有線', '奇妙', '77台', '78台', '79台']):
            return 'HOY TV'
        elif any(keyword in name_upper for keyword in ['RTHK', '香港電台', '港台']):
            return 'RTHK'
        
        # 然後檢查頻道類型
        for category, keywords in self.channel_categories.items():
            for keyword in keywords:
                if keyword.upper() in name_upper or keyword.upper() in group_upper:
                    return category
        
        return '其他'
    
    def determine_language(self, name, group):
        """確定語言"""
        name_upper = name.upper()
        group_upper = group.upper()
        
        for language, keywords in self.language_map.items():
            for keyword in keywords:
                if keyword.upper() in name_upper or keyword.upper() in group_upper:
                    return language
        
        return '未知'
    
    def determine_resolution(self, name, url):
        """確定清晰度"""
        name_upper = name.upper()
        
        # 從名稱中判斷
        if '4K' in name_upper or 'UHD' in name_upper:
            return '4K'
        elif '1080' in name_upper or 'FHD' in name_upper:
            return '1080p'
        elif '720' in name_upper or 'HD' in name_upper:
            return '720p'
        elif '480' in name_upper or 'SD' in name_upper:
            return '480p'
        
        return '未知'
    
    def extract_channel_id(self, name):
        """提取頻道ID/編號"""
        # 嘗試從名稱中提取數字ID
        match = re.search(r'\[(\d+)\]', name)
        if match:
            return match.group(1)
        
        # 嘗試提取TVB頻道號
        match = re.search(r'(翡翠|明珠|J2|無綫)([一二三四五六七八九\d]+)(台|臺|頻道)?', name)
        if match:
            channel_map = {'一': '1', '二': '2', '三': '3', '四': '4', '五': '5', 
                          '六': '6', '七': '7', '八': '8', '九': '9'}
            channel_num = match.group(2)
            for cn, num in channel_map.items():
                channel_num = channel_num.replace(cn, num)
            return channel_num
        
        return None
    
    def remove_duplicates(self):
        """去重處理"""
        unique_sources = []
        seen_urls = set()
        
        for source in self.sources:
            # 標準化URL
            normalized_url = source['url'].split('?')[0].rstrip('/')
            if normalized_url not in seen_urls:
                unique_sources.append(source)
                seen_urls.add(normalized_url)
        
        return unique_sources
    
    def make_request(self, url):
        """通用請求函數"""
        try:
            response = requests.get(url, timeout=self.timeout, headers=self.headers)
            if response.status_code == 200:
                return response.text
        except Exception as e:
            print(f"請求失敗 {url}: {e}")
        return None
    
    def parse_m3u_content(self, content, source_name, filter_hk=True):
        """解析M3U內容"""
        sources = []
        if not content:
            return sources
        
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('#EXTINF:'):
                # 提取頻道信息
                params = {}
                name = line.split(',')[-1] if ',' in line else f"Unknown_{source_name}"
                
                # 解析參數
                params_match = re.search(r'#EXTINF:.*?,(.*)', line)
                if params_match:
                    name = params_match.group(1).strip()
                
                param_matches = re.findall(r'([^=]+)="([^"]*)"', line)
                for key, value in param_matches:
                    params[key] = value
                
                # 獲取URL
                if i + 1 < len(lines):
                    url_line = lines[i + 1].strip()
                    if url_line and not url_line.startswith('#'):
                        group = params.get('group-title', source_name)
                        
                        # 篩選香港相關頻道
                        if not filter_hk or self.is_hk_channel(name, group):
                            sources.append({
                                "name": name,
                                "url": url_line,
                                "group": group,
                                "source": source_name
                            })
                        i += 1  # 跳過URL行
            i += 1
        
        return sources
    
    def is_hk_channel(self, name, group):
        """判斷是否為香港頻道"""
        hk_keywords = ['香港', 'HK', 'TVB', '翡翠', '明珠', 'ViuTV', 'RTHK', '鳳凰', '鳳凰', '香港開電視', 'J2', '無綫', 'HOY']
        name_upper = name.upper()
        group_upper = group.upper()
        
        for keyword in hk_keywords:
            if keyword.upper() in name_upper or keyword.upper() in group_upper:
                return True
        return False
    
    def add_sources(self, new_sources):
        """添加源到列表"""
        self.sources.extend(new_sources)
    
    # 以下是各個來源的獲取方法
    def fetch_fanmingming_ipv6(self):
        """獲取范明明IPv6直播源"""
        url = "https://live.fanmingming.com/tv/m3u/ipv6.m3u"
        content = self.make_request(url)
        if content:
            sources = self.parse_m3u_content(content, "范明明IPv6")
            self.add_sources(sources)
            print(f"從范明明IPv6獲取到 {len(sources)} 個香港頻道")
        return len(sources) if content else 0
    
    def fetch_fanmingming_v6(self):
        """獲取范明明v6直播源"""
        url = "https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/v6.m3u"
        content = self.make_request(url)
        if content:
            sources = self.parse_m3u_content(content, "范明明v6")
            self.add_sources(sources)
            print(f"從范明明v6獲取到 {len(sources)} 個香港頻道")
        return len(sources) if content else 0
    
    def fetch_iptv_org_hk(self):
        """獲取iptv-org香港直播源"""
        url = "https://iptv-org.github.io/iptv/countries/hk.m3u"
        content = self.make_request(url)
        if content:
            sources = self.parse_m3u_content(content, "iptv-org", filter_hk=False)
            self.add_sources(sources)
            print(f"從iptv-org獲取到 {len(sources)} 個香港頻道")
        return len(sources) if content else 0
    
    def fetch_epg_pw_hk(self):
        """獲取epg.pw香港頻道"""
        url = "https://epg.pw/test_channels_hong_kong.m3u"
        content = self.make_request(url)
        if content:
            sources = self.parse_m3u_content(content, "epg.pw", filter_hk=False)
            self.add_sources(sources)
            print(f"從epg.pw獲取到 {len(sources)} 個香港頻道")
        return len(sources) if content else 0
    
    def fetch_aktv(self):
        """獲取AKTV直播源"""
        url = "https://aktv.space/live.m3u"
        content = self.make_request(url)
        if content:
            sources = self.parse_m3u_content(content, "AKTV")
            self.add_sources(sources)
            print(f"從AKTV獲取到 {len(sources)} 個香港頻道")
        return len(sources) if content else 0
    
    def fetch_yuechan(self):
        """獲取YueChan直播源"""
        url = "https://raw.githubusercontent.com/YueChan/Live/main/IPTV.m3u"
        content = self.make_request(url)
        if content:
            sources = self.parse_m3u_content(content, "YueChan")
            self.add_sources(sources)
            print(f"從YueChan獲取到 {len(sources)} 個香港頻道")
        return len(sources) if content else 0
    
    def fetch_bigbiggrandg(self):
        """獲取BigBigGrandG直播源"""
        url = "https://raw.githubusercontent.com/BigBigGrandG/IPTV-URL/release/Gather.m3u"
        content = self.make_request(url)
        if content:
            sources = self.parse_m3u_content(content, "BigBigGrandG")
            self.add_sources(sources)
            print(f"從BigBigGrandG獲取到 {len(sources)} 個香港頻道")
        return len(sources) if content else 0
    
    def sort_sources(self, sources):
        """按照分類優先級和頻道名稱排序"""
        # 創建分類索引映射
        category_index = {category: idx for idx, category in enumerate(self.category_order)}
        
        # 對不在預定義分類中的頻道，給一個很大的索引值，使其排在最後
        def get_category_index(category):
            return category_index.get(category, len(self.category_order))
        
        # 按分類優先級和頻道名稱排序
        return sorted(sources, key=lambda x: (get_category_index(x['category']), x['name']))
    
    def generate_output_files(self, sources):
        """生成輸出文件"""
        # 按照分類優先級和頻道名稱排序
        sorted_sources = self.sort_sources(sources)
        
        # 生成M3U文件
        m3u_content = "#EXTM3U\n"
        for source in sorted_sources:
            m3u_content += f'#EXTINF:-1 tvg-id="{source.get("channel_id", "")}" tvg-name="{source["name"]}" tvg-logo="" group-title="{source["category"]}",{source["name"]}\n'
            m3u_content += f'{source["url"]}\n'
        
        with open("hk_tv_sources.m3u", "w", encoding="utf-8") as f:
            f.write(m3u_content)
        
        # 生成TXT文件
        txt_content = "# 香港電視直播源\n"
        txt_content += f"# 更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        txt_content += "# 來源: 多個公開直播源倉庫\n"
        txt_content += "# 此文件由GitHub Actions自動生成，每2天更新一次\n"
        txt_content += "# 已通過連接測試，響應時間越短的源越穩定\n\n"
        
        # 按分類組織頻道
        categories = {}
        for source in sorted_sources:
            category = source["category"]
            if category not in categories:
                categories[category] = []
            categories[category].append(source)
        
        # 按分類優先級排序
        sorted_categories = sorted(categories.items(), key=lambda x: self.category_order.index(x[0]) if x[0] in self.category_order else len(self.category_order))
        
        # 按分類輸出
        for category, channels in sorted_categories:
            txt_content += f"\n# {category}\n"
            for channel in channels:
                hd_flag = "[HD]" if channel.get('hd') else ""
                response_time = channel.get('response_time', 9999)
                time_info = f"[{response_time}ms]" if response_time < 9999 else "[超時]"
                txt_content += f"{channel['name']}{hd_flag}{time_info},{channel['url']}\n"
        
        with open("hk_tv_sources.txt", "w", encoding="utf-8") as f:
            f.write(txt_content)
        
        print(f"已生成 hk_tv_sources.m3u 和 hk_tv_sources.txt")
        print(f"M3U文件包含 {len(sources)} 個頻道")
    
    def generate_api_files(self, sources):
        """生成API文件，支持分類篩選"""
        # 創建API目錄
        os.makedirs("api", exist_ok=True)
        
        # 按照分類優先級和頻道名稱排序
        sorted_sources = self.sort_sources(sources)
        
        # 生成完整的頻道列表JSON
        api_data = {
            "last_updated": datetime.now().isoformat(),
            "total_channels": len(sorted_sources),
            "channels": sorted_sources
        }
        
        with open("api/all.json", "w", encoding="utf-8") as f:
            json.dump(api_data, f, ensure_ascii=False, indent=2)
        
        # 按分類生成API文件
        categories = {}
        for source in sorted_sources:
            category = source["category"]
            if category not in categories:
                categories[category] = []
            categories[category].append(source)
        
        # 按分類優先級排序
        sorted_categories = sorted(categories.items(), key=lambda x: self.category_order.index(x[0]) if x[0] in self.category_order else len(self.category_order))
        
        for category, channels in sorted_categories:
            category_data = {
                "category": category,
                "count": len(channels),
                "channels": channels
            }
            
            # 創建分類目錄
            category_dir = f"api/category/{category}"
            os.makedirs(category_dir, exist_ok=True)
            
            with open(f"{category_dir}/index.json", "w", encoding="utf-8") as f:
                json.dump(category_data, f, ensure_ascii=False, indent=2)
        
        # 按語言生成API文件
        languages = {}
        for source in sorted_sources:
            language = source["language"]
            if language not in languages:
                languages[language] = []
            languages[language].append(source)
        
        for language, channels in languages.items():
            language_data = {
                "language": language,
                "count": len(channels),
                "channels": channels
            }
            
            # 創建語言目錄
            language_dir = f"api/language/{language}"
            os.makedirs(language_dir, exist_ok=True)
            
            with open(f"{language_dir}/index.json", "w", encoding="utf-8") as f:
                json.dump(language_data, f, ensure_ascii=False, indent=2)
        
        # 生成高清頻道API
        hd_channels = [s for s in sorted_sources if s.get('hd')]
        hd_data = {
            "hd_channels": True,
            "count": len(hd_channels),
            "channels": hd_channels
        }
        
        os.makedirs("api/filters", exist_ok=True)
        with open("api/filters/hd.json", "w", encoding="utf-8") as f:
            json.dump(hd_data, f, ensure_ascii=False, indent=2)
        
        # 生成快速響應頻道API
        fast_channels = [s for s in sorted_sources if s.get('response_time', 9999) < 1000]
        fast_data = {
            "fast_channels": True,
            "count": len(fast_channels),
            "channels": fast_channels
        }
        
        with open("api/filters/fast.json", "w", encoding="utf-8") as f:
            json.dump(fast_data, f, ensure_ascii=False, indent=2)
        
        print("已生成API文件")

def main():
    """主函數"""
    fetcher = HKTVSourceFetcher()
    sources = fetcher.fetch_all_sources()
    
    # 如果沒有獲取到任何源，使用備用源
    if not sources:
        print("使用備用直播源...")
        backup_sources = [
            {"name": "TVB翡翠台", "url": "http://example.com/tvb1.m3u8", "group": "香港", "source": "備用", 
             "category": "TVB", "language": "粵語", "resolution": "1080p", "hd": True, "channel_id": "81", "response_time": 100},
            {"name": "TVB明珠台", "url": "http://example.com/tvb2.m3u8", "group": "香港", "source": "備用",
             "category": "TVB", "language": "英語", "resolution": "1080p", "hd": True, "channel_id": "84", "response_time": 100},
            {"name": "ViuTV", "url": "http://example.com/viutv.m3u8", "group": "香港", "source": "備用",
             "category": "ViuTV", "language": "粵語", "resolution": "1080p", "hd": True, "channel_id": "99", "response_time": 100},
            {"name": "HOY TV", "url": "http://example.com/hoytv.m3u8", "group": "香港", "source": "備用",
             "category": "HOY TV", "language": "粵語", "resolution": "720p", "hd": False, "channel_id": "77", "response_time": 100},
            {"name": "RTHK 31", "url": "http://example.com/rthk31.m3u8", "group": "香港", "source": "備用",
             "category": "RTHK", "language": "粵語", "resolution": "720p", "hd": False, "channel_id": "31", "response_time": 100},
            {"name": "RTHK 32", "url": "http://example.com/rthk32.m3u8", "group": "香港", "source": "備用",
             "category": "RTHK", "language": "普通話", "resolution": "720p", "hd": False, "channel_id": "32", "response_time": 100}
        ]
        fetcher.generate_output_files(backup_sources)
        fetcher.generate_api_files(backup_sources)

if __name__ == "__main__":
    main()
