# scripts/fetch_hk_tv_sources.py
import requests
import re
import time
import json
import os  # 添加这行导入
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, parse_qs

class HKTVSourceFetcher:
    def __init__(self):
        self.sources = []
        self.timeout = 15
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # 频道分类映射
        self.channel_categories = {
            # 新闻频道
            '新闻': ['新闻', 'NEWS', '資訊', '財經', '财经', 'NEWS', 'INFO'],
            # 综合频道
            '综合': ['綜合', '综合', '翡翠', '明珠', 'J2', 'ViuTV', '開電視', '开电视', 'RTHK', '鳳凰', '凤凰'],
            # 体育频道
            '体育': ['體育', '体育', 'SPORTS', '賽馬', '赛马', '足球', '籃球', '篮球'],
            # 电影频道
            '电影': ['電影', '电影', 'MOVIE', '影院', '戲劇', '戏剧'],
            # 儿童频道
            '儿童': ['兒童', '儿童', 'KIDS', '卡通', '動畫', '动画'],
            # 国际频道
            '国际': ['國際', '国际', 'WORLD', 'BBC', 'CNN', 'NHK', 'DW'],
        }
        # 语言映射
        self.language_map = {
            '粤语': ['粵語', '粤语', 'CANTONESE', '廣東話', '广东话'],
            '普通话': ['普通話', '普通话', 'MANDARIN', '國語', '国语'],
            '英语': ['英語', '英语', 'ENGLISH'],
            '多语言': ['雙語', '双语', '多語', '多语', 'BILINGUAL']
        }
    
    def fetch_all_sources(self):
        """从所有可用来源获取直播源"""
        print("开始获取香港电视直播源...")
        
        # 定义所有来源
        sources_methods = [
            self.fetch_fanmingming_ipv6,
            self.fetch_fanmingming_v6,
            self.fetch_iptv_org_hk,
            self.fetch_epg_pw_hk,
            self.fetch_aktv,
            self.fetch_ftindy_sources,
            self.fetch_yuechan,
            self.fetch_bigbiggrandg,
            self.fetch_yang1989,
            self.fetch_zhanghongguang
        ]
        
        # 使用多线程并行获取
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_method = {executor.submit(method): method.__name__ for method in sources_methods}
            
            for future in as_completed(future_to_method):
                method_name = future_to_method[future]
                try:
                    result = future.result()
                    print(f"{method_name} 完成")
                except Exception as e:
                    print(f"{method_name} 出错: {e}")
        
        # 去重处理
        unique_sources = self.remove_duplicates()
        
        # 分类和增强元数据
        enhanced_sources = self.enhance_metadata(unique_sources)
        
        print(f"总共获取到 {len(enhanced_sources)} 个唯一香港频道")
        
        # 生成输出文件
        self.generate_output_files(enhanced_sources)
        
        # 生成API文件
        self.generate_api_files(enhanced_sources)
        
        return enhanced_sources
    
    def enhance_metadata(self, sources):
        """增强频道元数据：分类、语言、清晰度等"""
        enhanced_sources = []
        
        for source in sources:
            # 确定频道分类
            category = self.determine_category(source['name'], source.get('group', ''))
            source['category'] = category
            
            # 确定语言
            language = self.determine_language(source['name'], source.get('group', ''))
            source['language'] = language
            
            # 确定清晰度
            resolution = self.determine_resolution(source['name'], source['url'])
            source['resolution'] = resolution
            
            # 确定是否高清
            source['hd'] = '高清' in source['name'] or 'HD' in source['name'].upper() or resolution in ['1080p', '720p']
            
            # 提取频道ID/编号
            channel_id = self.extract_channel_id(source['name'])
            source['channel_id'] = channel_id
            
            enhanced_sources.append(source)
        
        return enhanced_sources
    
    def determine_category(self, name, group):
        """确定频道分类"""
        name_upper = name.upper()
        group_upper = group.upper()
        
        for category, keywords in self.channel_categories.items():
            for keyword in keywords:
                if keyword.upper() in name_upper or keyword.upper() in group_upper:
                    return category
        
        return '其他'
    
    def determine_language(self, name, group):
        """确定语言"""
        name_upper = name.upper()
        group_upper = group.upper()
        
        for language, keywords in self.language_map.items():
            for keyword in keywords:
                if keyword.upper() in name_upper or keyword.upper() in group_upper:
                    return language
        
        return '未知'
    
    def determine_resolution(self, name, url):
        """确定清晰度"""
        name_upper = name.upper()
        
        # 从名称中判断
        if '4K' in name_upper or 'UHD' in name_upper:
            return '4K'
        elif '1080' in name_upper or 'FHD' in name_upper:
            return '1080p'
        elif '720' in name_upper or 'HD' in name_upper:
            return '720p'
        elif '480' in name_upper or 'SD' in name_upper:
            return '480p'
        
        # 从URL参数中判断
        try:
            parsed_url = urlparse(url)
            query_params = parse_qs(parsed_url.query)
            
            if 'bitrate' in query_params:
                bitrate = int(query_params['bitrate'][0])
                if bitrate > 8000:
                    return '4K'
                elif bitrate > 4000:
                    return '1080p'
                elif bitrate > 2000:
                    return '720p'
                else:
                    return '480p'
        except:
            pass
        
        return '未知'
    
    def extract_channel_id(self, name):
        """提取频道ID/编号"""
        # 尝试从名称中提取数字ID
        match = re.search(r'\[(\d+)\]', name)
        if match:
            return match.group(1)
        
        # 尝试提取TVB频道号
        match = re.search(r'(翡翠|明珠|J2|無綫|无线)([一二三四五六七八九\d]+)(台|臺|频道)?', name)
        if match:
            channel_map = {'一': '1', '二': '2', '三': '3', '四': '4', '五': '5', 
                          '六': '6', '七': '7', '八': '8', '九': '9'}
            channel_num = match.group(2)
            for cn, num in channel_map.items():
                channel_num = channel_num.replace(cn, num)
            return channel_num
        
        return None
    
    def remove_duplicates(self):
        """去重处理"""
        unique_sources = []
        seen_urls = set()
        
        for source in self.sources:
            # 标准化URL
            normalized_url = source['url'].split('?')[0].rstrip('/')
            if normalized_url not in seen_urls:
                unique_sources.append(source)
                seen_urls.add(normalized_url)
        
        return unique_sources
    
    def make_request(self, url):
        """通用请求函数"""
        try:
            response = requests.get(url, timeout=self.timeout, headers=self.headers)
            if response.status_code == 200:
                return response.text
        except Exception as e:
            print(f"请求失败 {url}: {e}")
        return None
    
    def parse_m3u_content(self, content, source_name, filter_hk=True):
        """解析M3U内容"""
        sources = []
        if not content:
            return sources
        
        lines = content.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            if line.startswith('#EXTINF:'):
                # 提取频道信息
                params = {}
                name = line.split(',')[-1] if ',' in line else f"Unknown_{source_name}"
                
                # 解析参数
                params_match = re.search(r'#EXTINF:.*?,(.*)', line)
                if params_match:
                    name = params_match.group(1).strip()
                
                param_matches = re.findall(r'([^=]+)="([^"]*)"', line)
                for key, value in param_matches:
                    params[key] = value
                
                # 获取URL
                if i + 1 < len(lines):
                    url_line = lines[i + 1].strip()
                    if url_line and not url_line.startswith('#'):
                        group = params.get('group-title', source_name)
                        
                        # 筛选香港相关频道
                        if not filter_hk or self.is_hk_channel(name, group):
                            sources.append({
                                "name": name,
                                "url": url_line,
                                "group": group,
                                "source": source_name
                            })
                        i += 1  # 跳过URL行
            i += 1
        
        return sources
    
    def is_hk_channel(self, name, group):
        """判断是否为香港频道"""
        hk_keywords = ['香港', 'HK', 'TVB', '翡翠', '明珠', 'ViuTV', 'RTHK', '鳳凰', '凤凰', '香港开电视', 'J2', '無綫', '无线']
        name_upper = name.upper()
        group_upper = group.upper()
        
        for keyword in hk_keywords:
            if keyword.upper() in name_upper or keyword.upper() in group_upper:
                return True
        return False
    
    def add_sources(self, new_sources):
        """添加源到列表"""
        self.sources.extend(new_sources)
    
    # 以下是各个来源的获取方法
    def fetch_fanmingming_ipv6(self):
        """获取范明明IPv6直播源"""
        url = "https://live.fanmingming.com/tv/m3u/ipv6.m3u"
        content = self.make_request(url)
        if content:
            sources = self.parse_m3u_content(content, "范明明IPv6")
            self.add_sources(sources)
            print(f"从范明明IPv6获取到 {len(sources)} 个香港频道")
        return len(sources) if content else 0
    
    def fetch_fanmingming_v6(self):
        """获取范明明v6直播源"""
        url = "https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/v6.m3u"
        content = self.make_request(url)
        if content:
            sources = self.parse_m3u_content(content, "范明明v6")
            self.add_sources(sources)
            print(f"从范明明v6获取到 {len(sources)} 个香港频道")
        return len(sources) if content else 0
    
    def fetch_iptv_org_hk(self):
        """获取iptv-org香港直播源"""
        url = "https://iptv-org.github.io/iptv/countries/hk.m3u"
        content = self.make_request(url)
        if content:
            sources = self.parse_m3u_content(content, "iptv-org", filter_hk=False)
            self.add_sources(sources)
            print(f"从iptv-org获取到 {len(sources)} 个香港频道")
        return len(sources) if content else 0
    
    def fetch_epg_pw_hk(self):
        """获取epg.pw香港频道"""
        url = "https://epg.pw/test_channels_hong_kong.m3u"
        content = self.make_request(url)
        if content:
            sources = self.parse_m3u_content(content, "epg.pw", filter_hk=False)
            self.add_sources(sources)
            print(f"从epg.pw获取到 {len(sources)} 个香港频道")
        return len(sources) if content else 0
    
    def fetch_aktv(self):
        """获取AKTV直播源"""
        url = "https://aktv.space/live.m3u"
        content = self.make_request(url)
        if content:
            sources = self.parse_m3u_content(content, "AKTV")
            self.add_sources(sources)
            print(f"从AKTV获取到 {len(sources)} 个香港频道")
        return len(sources) if content else 0
    
    def fetch_ftindy_sources(self):
        """获取Ftindy多个直播源"""
        ftindy_urls = [
            ("https://raw.githubusercontent.com/Ftindy/IPTV-URL/main/bestv.m3u", "Ftindy百视通"),
            ("https://raw.githubusercontent.com/Ftindy/IPTV-URL/main/cqyx.m3u", "Ftindy重庆广电"),
            ("https://raw.githubusercontent.com/Ftindy/IPTV-URL/main/IPTV.m3u", "Ftindy国内4K")
        ]
        
        total_sources = 0
        for url, name in ftindy_urls:
            content = self.make_request(url)
            if content:
                sources = self.parse_m3u_content(content, name)
                self.add_sources(sources)
                total_sources += len(sources)
                print(f"从{name}获取到 {len(sources)} 个香港频道")
            time.sleep(1)  # 避免请求过快
        
        return total_sources
    
    def fetch_yuechan(self):
        """获取YueChan直播源"""
        url = "https://raw.githubusercontent.com/YueChan/Live/main/IPTV.m3u"
        content = self.make_request(url)
        if content:
            sources = self.parse_m3u_content(content, "YueChan")
            self.add_sources(sources)
            print(f"从YueChan获取到 {len(sources)} 个香港频道")
        return len(sources) if content else 0
    
    def fetch_bigbiggrandg(self):
        """获取BigBigGrandG直播源"""
        url = "https://raw.githubusercontent.com/BigBigGrandG/IPTV-URL/release/Gather.m3u"
        content = self.make_request(url)
        if content:
            sources = self.parse_m3u_content(content, "BigBigGrandG")
            self.add_sources(sources)
            print(f"从BigBigGrandG获取到 {len(sources)} 个香港频道")
        return len(sources) if content else 0
    
    def fetch_yang1989(self):
        """获取YanG-1989直播源"""
        url = "https://raw.githubusercontent.com/YanG-1989/m3u/main/Gather.m3u"
        content = self.make_request(url)
        if content:
            sources = self.parse_m3u_content(content, "YanG-1989")
            self.add_sources(sources)
            print(f"从YanG-1989获取到 {len(sources)} 个香港频道")
        return len(sources) if content else 0
    
    def fetch_zhanghongguang(self):
        """获取ZhangHongGuang直播源"""
        url = "https://raw.githubusercontent.com/zhanghongguang/zhanghongguang.github.io/main/IPV6_IPTV.m3u"
        content = self.make_request(url)
        if content:
            sources = self.parse_m3u_content(content, "ZhangHongGuang")
            self.add_sources(sources)
            print(f"从ZhangHongGuang获取到 {len(sources)} 个香港频道")
        return len(sources) if content else 0
    
    def generate_output_files(self, sources):
        """生成输出文件"""
        # 生成M3U文件
        m3u_content = "#EXTM3U\n"
        for source in sources:
            m3u_content += f'#EXTINF:-1 tvg-id="{source.get("channel_id", "")}" tvg-name="{source["name"]}" tvg-logo="" group-title="{source["category"]}",{source["name"]}\n'
            m3u_content += f'{source["url"]}\n'
        
        with open("hk_tv_sources.m3u", "w", encoding="utf-8") as f:
            f.write(m3u_content)
        
        # 生成TXT文件
        txt_content = "# 香港电视直播源\n"
        txt_content += f"# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        txt_content += "# 来源: 多个公开直播源仓库\n"
        txt_content += "# 此文件由GitHub Actions自动生成，每2天更新一次\n\n"
        
        # 按分类组织频道
        categories = {}
        for source in sources:
            category = source["category"]
            if category not in categories:
                categories[category] = []
            categories[category].append(source)
        
        # 按分类输出
        for category, channels in categories.items():
            txt_content += f"\n# {category}\n"
            for channel in channels:
                hd_flag = "[HD]" if channel.get('hd') else ""
                txt_content += f"{channel['name']}{hd_flag},{channel['url']}\n"
        
        with open("hk_tv_sources.txt", "w", encoding="utf-8") as f:
            f.write(txt_content)
        
        print(f"已生成 hk_tv_sources.m3u 和 hk_tv_sources.txt")
        print(f"M3U文件包含 {len(sources)} 个频道")
    
    def generate_api_files(self, sources):
        """生成API文件，支持分类筛选"""
        # 创建API目录
        os.makedirs("api", exist_ok=True)
        
        # 生成完整的频道列表JSON
        api_data = {
            "last_updated": datetime.now().isoformat(),
            "total_channels": len(sources),
            "channels": sources
        }
        
        with open("api/all.json", "w", encoding="utf-8") as f:
            json.dump(api_data, f, ensure_ascii=False, indent=2)
        
        # 按分类生成API文件
        categories = {}
        for source in sources:
            category = source["category"]
            if category not in categories:
                categories[category] = []
            categories[category].append(source)
        
        for category, channels in categories.items():
            category_data = {
                "category": category,
                "count": len(channels),
                "channels": channels
            }
            
            # 创建分类目录
            category_dir = f"api/category/{category}"
            os.makedirs(category_dir, exist_ok=True)
            
            with open(f"{category_dir}/index.json", "w", encoding="utf-8") as f:
                json.dump(category_data, f, ensure_ascii=False, indent=2)
        
        # 按语言生成API文件
        languages = {}
        for source in sources:
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
            
            # 创建语言目录
            language_dir = f"api/language/{language}"
            os.makedirs(language_dir, exist_ok=True)
            
            with open(f"{language_dir}/index.json", "w", encoding="utf-8") as f:
                json.dump(language_data, f, ensure_ascii=False, indent=2)
        
        # 生成高清频道API
        hd_channels = [s for s in sources if s.get('hd')]
        hd_data = {
            "hd_channels": True,
            "count": len(hd_channels),
            "channels": hd_channels
        }
        
        os.makedirs("api/filters", exist_ok=True)
        with open("api/filters/hd.json", "w", encoding="utf-8") as f:
            json.dump(hd_data, f, ensure_ascii=False, indent=2)
        
        print("已生成API文件")

def main():
    """主函数"""
    fetcher = HKTVSourceFetcher()
    sources = fetcher.fetch_all_sources()
    
    # 如果没有获取到任何源，使用备用源
    if not sources:
        print("使用备用直播源...")
        backup_sources = [
            {"name": "TVB翡翠台", "url": "http://example.com/tvb1.m3u8", "group": "香港", "source": "备用", 
             "category": "综合", "language": "粤语", "resolution": "1080p", "hd": True, "channel_id": "81"},
            {"name": "TVB明珠台", "url": "http://example.com/tvb2.m3u8", "group": "香港", "source": "备用",
             "category": "综合", "language": "英语", "resolution": "1080p", "hd": True, "channel_id": "84"},
            {"name": "ViuTV", "url": "http://example.com/viutv.m3u8", "group": "香港", "source": "备用",
             "category": "综合", "language": "粤语", "resolution": "1080p", "hd": True, "channel_id": "99"},
            {"name": "香港开电视", "url": "http://example.com/hkotv.m3u8", "group": "香港", "source": "备用",
             "category": "综合", "language": "粤语", "resolution": "720p", "hd": False, "channel_id": "77"},
            {"name": "RTHK31", "url": "http://example.com/rthk31.m3u8", "group": "香港", "source": "备用",
             "category": "综合", "language": "粤语", "resolution": "720p", "hd": False, "channel_id": "31"},
            {"name": "RTHK32", "url": "http://example.com/rthk32.m3u8", "group": "香港", "source": "备用",
             "category": "综合", "language": "普通话", "resolution": "720p", "hd": False, "channel_id": "32"}
        ]
        fetcher.generate_output_files(backup_sources)
        fetcher.generate_api_files(backup_sources)

if __name__ == "__main__":
    main()
