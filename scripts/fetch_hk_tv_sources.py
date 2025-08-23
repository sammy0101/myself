# scripts/fetch_hk_tv_sources.py
import requests
import re
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

class HKTVSourceFetcher:
    def __init__(self):
        self.sources = []
        self.timeout = 15
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
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
        
        print(f"总共获取到 {len(unique_sources)} 个唯一香港频道")
        
        # 生成输出文件
        self.generate_output_files(unique_sources)
        
        return unique_sources
    
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
        hk_keywords = ['香港', 'HK', 'TVB', '翡翠', '明珠', 'ViuTV', 'RTHK', '凤凰卫视', '香港开电视', 'J2']
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
            m3u_content += f'#EXTINF:-1 tvg-id="" tvg-name="{source["name"]}" tvg-logo="" group-title="{source["group"]}",{source["name"]}\n'
            m3u_content += f'{source["url"]}\n'
        
        with open("hk_tv_sources.m3u", "w", encoding="utf-8") as f:
            f.write(m3u_content)
        
        # 生成TXT文件
        txt_content = "# 香港电视直播源\n"
        txt_content += f"# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        txt_content += "# 来源: 多个公开直播源仓库\n"
        txt_content += "# 此文件由GitHub Actions自动生成，每2天更新一次\n\n"
        
        # 按分组组织频道
        groups = {}
        for source in sources:
            group = source["group"]
            if group not in groups:
                groups[group] = []
            groups[group].append(source)
        
        # 按分组输出
        for group, channels in groups.items():
            txt_content += f"\n# {group}\n"
            for channel in channels:
                txt_content += f"{channel['name']},{channel['url']}\n"
        
        with open("hk_tv_sources.txt", "w", encoding="utf-8") as f:
            f.write(txt_content)
        
        print(f"已生成 hk_tv_sources.m3u 和 hk_tv_sources.txt")
        print(f"M3U文件包含 {len(sources)} 个频道")

def main():
    """主函数"""
    fetcher = HKTVSourceFetcher()
    sources = fetcher.fetch_all_sources()
    
    # 如果没有获取到任何源，使用备用源
    if not sources:
        print("使用备用直播源...")
        backup_sources = [
            {"name": "TVB翡翠台", "url": "http://example.com/tvb1.m3u8", "group": "香港", "source": "备用"},
            {"name": "TVB明珠台", "url": "http://example.com/tvb2.m3u8", "group": "香港", "source": "备用"},
            {"name": "ViuTV", "url": "http://example.com/viutv.m3u8", "group": "香港", "source": "备用"},
            {"name": "香港开电视", "url": "http://example.com/hkotv.m3u8", "group": "香港", "source": "备用"},
            {"name": "RTHK31", "url": "http://example.com/rthk31.m3u8", "group": "香港", "source": "备用"},
            {"name": "RTHK32", "url": "http://example.com/rthk32.m3u8", "group": "香港", "source": "备用"}
        ]
        fetcher.generate_output_files(backup_sources)

if __name__ == "__main__":
    main()
