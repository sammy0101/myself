# scripts/fetch_hk_tv_sources.py
import requests
import re
import time
import json
import os
import socket
import hashlib
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
        
        # 从文件加载自定义源
        self.custom_sources = self.load_custom_sources()
        
        # 定义分类优先级顺序
        self.category_order = [
            'TVB', 'ViuTV', 'HOY TV', 'RTHK', '新闻', '体育', '电影', '国际', '儿童', '其他'
        ]
        # 更精确的频道分类映射
        self.channel_categories = {
            # TVB频道
            'TVB': ['TVB', '無綫', '无线', '翡翠', '明珠', 'J2', 'J5', '無綫新聞', '無綫財經', '無綫綜藝'],
            # ViuTV频道
            'ViuTV': ['ViuTV', 'Viu', 'VIU'],
            # HOY TV频道 (前开电视)
            'HOY TV': ['HOY', '開電視', '开电视', '有線', '有线', '奇妙', '77台', '78台', '79台'],
            # RTHK频道
            'RTHK': ['RTHK', '香港电台', '港台'],
            # 新闻频道
            '新闻': ['新聞', '新闻', 'NEWS', '資訊', '財經', '财经', 'INFO', '財經資訊', '财经资讯'],
            # 体育频道
            '体育': ['體育', '体育', 'SPORTS', '賽馬', '赛马', '足球', '籃球', '篮球', '運動', '运动'],
            # 电影频道
            '电影': ['電影', '电影', 'MOVIE', '影院', '戲劇', '戏剧', 'CINEMA'],
            # 国际频道
            '国际': ['國際', '国际', 'WORLD', 'BBC', 'CNN', 'NHK', 'DW', '凤凰卫视', '鳳凰衛視'],
            # 儿童频道
            '儿童': ['兒童', '儿童', 'KIDS', '卡通', '動畫', '动画'],
        }
        # 语言映射
        self.language_map = {
            '粤语': ['粵語', '粤语', 'CANTONESE', '廣東話', '广东话'],
            '普通话': ['普通話', '普通话', 'MANDARIN', '國語', '国语'],
            '英语': ['英語', '英语', 'ENGLISH'],
            '多语言': ['雙語', '双语', '多語', '多语', 'BILINGUAL']
        }
        
        # 扩展香港频道关键词
        self.hk_keywords = [
            '香港', 'HK', 'TVB', '翡翠', '明珠', 'ViuTV', 'VIU', 'RTHK', '鳳凰', '凤凰', 
            '香港开电视', 'J2', '無綫', '无线', 'HOY', '開電視', '开电视', '有線', '有线',
            '奇妙', '77台', '78台', '79台', '港台', '香港电台', '澳門', 'Macau', '澳视',
            '澳門衛視', '澳廣視', 'TDM'
        ]
    
    def load_custom_sources(self):
        """从custom_sources.txt文件加载自定义源"""
        custom_sources = []
        custom_file = "custom_sources.txt"
        
        if os.path.exists(custom_file):
            try:
                with open(custom_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        line = line.strip()
                        # 跳过空行和注释行
                        if not line or line.startswith('#'):
                            continue
                        
                        # 提取URL
                        url = line
                        
                        # 从URL中提取名称
                        parsed_url = urlparse(url)
                        name = f"自定义源_{parsed_url.netloc}"
                        
                        custom_sources.append({
                            "name": name,
                            "url": url,
                            "filter_hk": True  # 默认只筛选香港频道
                        })
            except Exception as e:
                print(f"读取自定义源文件时出错: {e}")
        
        print(f"从自定义文件加载了 {len(custom_sources)} 个源")
        return custom_sources
    
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
            self.fetch_yuechan,
            self.fetch_bigbiggrandg,
        ]
        
        # 添加自定义源获取方法
        for i, custom_source in enumerate(self.custom_sources):
            method_name = f"fetch_custom_{i}"
            method = lambda src=custom_source: self.fetch_custom_source(src, f"自定义源_{i+1}")
            sources_methods.append(method)
        
        # 使用多线程并行获取
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_method = {}
            for method in sources_methods:
                future = executor.submit(method)
                method_name = method.__name__ if hasattr(method, '__name__') else "custom_method"
                future_to_method[future] = method_name
            
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
        
        print(f"总共获取到 {len(enhanced_sources)} 个香港频道")
        
        # 测试连接并过滤无效源
        tested_sources = self.test_sources_connectivity(enhanced_sources)
        
        print(f"连接测试后剩余 {len(tested_sources)} 个有效频道")
        
        # 生成输出文件
        self.generate_output_files(tested_sources)
        
        return tested_sources
    
    def fetch_custom_source(self, source_config, source_name):
        """获取自定义直播源"""
        url = source_config['url']
        filter_hk = source_config.get('filter_hk', True)
        
        content = self.make_request(url)
        if content:
            sources = self.parse_m3u_content(content, source_name, filter_hk=filter_hk)
            self.add_sources(sources)
            print(f"从{source_name}获取到 {len(sources)} 个频道")
            return len(sources)
        return 0
    
    def test_sources_connectivity(self, sources):
        """测试源的连接性并过滤无效源"""
        print("开始测试频道连接性...")
        
        valid_sources = []
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            # 创建测试任务
            future_to_source = {
                executor.submit(self.test_source_connectivity, source): source 
                for source in sources
            }
            
            # 处理结果
            for i, future in enumerate(as_completed(future_to_source)):
                source = future_to_source[future]
                try:
                    is_valid, response_time, error_type = future.result()
                    if is_valid:
                        source['response_time'] = response_time
                        valid_sources.append(source)
                        print(f"✓ {source['name']} - {response_time}ms")
                    else:
                        print(f"✗ {source['name']} - {error_type}")
                except Exception as e:
                    print(f"✗ {source['name']} - 测试错误: {e}")
                
                # 每测试10个源显示一次进度
                if (i + 1) % 10 == 0:
                    print(f"已测试 {i + 1}/{len(sources)} 个频道")
        
        return valid_sources
    
    def test_source_connectivity(self, source):
        """测试单个源的连接性"""
        url = source['url']
        
        # 跳过明显无效的URL
        if not url or url.startswith('http://example.com'):
            return False, 9999, "无效URL"
        
        try:
            # 使用带Range头的GET请求，只请求少量数据
            headers = self.headers.copy()
            headers['Range'] = 'bytes=0-1024'  # 只请求前1KB数据
            
            start_time = time.time()
            response = requests.get(
                url, 
                timeout=5, 
                headers=headers,
                stream=True
            )
            # 读取少量数据确认流可用
            for chunk in response.iter_content(chunk_size=512):
                if chunk:
                    break
                    
            response_time = int((time.time() - start_time) * 1000)
            
            if response.status_code in (200, 206):  # 200 OK或206部分内容
                return True, response_time, "成功"
            else:
                return False, response_time, f"HTTP错误: {response.status_code}"
                
        except requests.RequestException as e:
            return False, 9999, f"HTTP请求错误: {e}"
        except socket.timeout:
            return False, 9999, "连接超时"
        except socket.gaierror:
            return False, 9999, "DNS解析失败"
        except OSError as e:
            return False, 9999, f"系统错误: {e}"
    
    def enhance_metadata(self, sources):
        """增强频道元数据：分类、语言、清晰度等"""
        enhanced_sources = []
        
        for source in sources:
            # 确定频道分类 - 使用更精确的分类方法
            category = self.determine_category_precise(source['name'], source.get('group', ''))
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
    
    def determine_category_precise(self, name, group):
        """更精确地确定频道分类"""
        name_upper = name.upper()
        group_upper = group.upper()
        
        # 首先检查特定频道
        if any(keyword in name_upper for keyword in ['TVB', '無綫', '无线', '翡翠', '明珠', 'J2']):
            return 'TVB'
        elif any(keyword in name_upper for keyword in ['VIUTV', 'VIU TV']):
            return 'ViuTV'
        elif any(keyword in name_upper for keyword in ['HOY', '開電視', '开电视', '有線', '有线', '奇妙', '77台', '78台', '79台']):
            return 'HOY TV'
        elif any(keyword in name_upper for keyword in ['RTHK', '香港电台', '港台']):
            return 'RTHK'
        
        # 然后检查频道类型
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
    
    def make_request(self, url, use_cache=True):
        """通用请求函数，支持缓存"""
        cache_dir = "cache"
        os.makedirs(cache_dir, exist_ok=True)
        
        # 生成缓存文件名
        url_hash = hashlib.md5(url.encode()).hexdigest()
        cache_file = os.path.join(cache_dir, f"{url_hash}.cache")
        
        # 检查缓存是否有效（1小时内）
        if use_cache and os.path.exists(cache_file):
            file_age = time.time() - os.path.getmtime(cache_file)
            if file_age < 3600:  # 1小时缓存
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        return f.read()
                except:
                    pass  # 缓存读取失败，继续请求
        
        try:
            response = requests.get(url, timeout=self.timeout, headers=self.headers)
            if response.status_code == 200:
                content = response.text
                # 保存到缓存
                try:
                    with open(cache_file, 'w', encoding='utf-8') as f:
                        f.write(content)
                except:
                    pass  # 缓存写入失败不影响主流程
                return content
        except Exception as e:
            print(f"请求失败 {url}: {e}")
        
        return None
    
    def parse_m3u_content(self, content, source_name, filter_hk=True):
        """解析M3U内容"""
        sources = []
        if not content:
            return sources
        
        lines = content.split('\n')
        current_info = {}
        
        for line in lines:
            line = line.strip()
            if line.startswith('#EXTINF:'):
                # 重置当前频道信息
                current_info = {"params": {}, "name": ""}
                
                # 提取频道名称
                if ',' in line:
                    current_info["name"] = line.split(',', 1)[1].strip()
                
                # 解析参数
                param_matches = re.findall(r'(\w+)=["\']([^"\']*)["\']', line)
                for key, value in param_matches:
                    current_info["params"][key.lower()] = value
                
            elif line and not line.startswith('#') and current_info:
                # 这是URL行，且前面有EXTINF信息
                group = current_info["params"].get('group-title', source_name)
                name = current_info["name"] or f"Unknown_{source_name}"
                
                # 筛选香港相关频道
                if not filter_hk or self.is_hk_channel(name, group):
                    source_data = {
                        "name": name,
                        "url": line,
                        "group": group,
                        "source": source_name
                    }
                    # 添加所有解析到的参数
                    source_data.update(current_info["params"])
                    sources.append(source_data)
                
                # 重置当前信息
                current_info = {}
        
        return sources
    
    def is_hk_channel(self, name, group):
        """判断是否为香港频道"""
        name_upper = name.upper()
        group_upper = group.upper()
        
        for keyword in self.hk_keywords:
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
            return len(sources)
        return 0
    
    def fetch_fanmingming_v6(self):
        """获取范明明v6直播源"""
        url = "https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/v6.m3u"
        content = self.make_request(url)
        if content:
            sources = self.parse_m3u_content(content, "范明明v6")
            self.add_sources(sources)
            print(f"从范明明v6获取到 {len(sources)} 个香港频道")
            return len(sources)
        return 0
    
    def fetch_iptv_org_hk(self):
        """获取iptv-org香港直播源"""
        url = "https://iptv-org.github.io/iptv/countries/hk.m3u"
        content = self.make_request(url)
        if content:
            sources = self.parse_m3u_content(content, "iptv-org", filter_hk=False)
            self.add_sources(sources)
            print(f"从iptv-org获取到 {len(sources)} 个香港频道")
            return len(sources)
        return 0
    
    def fetch_epg_pw_hk(self):
        """获取epg.pw香港频道"""
        url = "https://epg.pw/test_channels_hong_kong.m3u"
        content = self.make_request(url)
        if content:
            sources = self.parse_m3u_content(content, "epg.pw", filter_hk=False)
            self.add_sources(sources)
            print(f"从epg.pw获取到 {len(sources)} 个香港频道")
            return len(sources)
        return 0
    
    def fetch_aktv(self):
        """获取AKTV直播源"""
        url = "https://aktv.space/live.m3u"
        content = self.make_request(url)
        if content:
            sources = self.parse_m3u_content(content, "AKTV")
            self.add_sources(sources)
            print(f"从AKTV获取到 {len(sources)} 个香港频道")
            return len(sources)
        return 0
    
    def fetch_yuechan(self):
        """获取YueChan直播源"""
        url = "https://raw.githubusercontent.com/YueChan/Live/main/IPTV.m3u"
        content = self.make_request(url)
        if content:
            sources = self.parse_m3u_content(content, "YueChan")
            self.add_sources(sources)
            print(f"从YueChan获取到 {len(sources)} 个香港频道")
            return len(sources)
        return 0
    
    def fetch_bigbiggrandg(self):
        """获取BigBigGrandG直播源"""
        url = "https://raw.githubusercontent.com/BigBigGrandG/IPTV-URL/release/Gather.m3u"
        content = self.make_request(url)
        if content:
            sources = self.parse_m3u_content(content, "BigBigGrandG")
            self.add_sources(sources)
            print(f"从BigBigGrandG获取到 {len(sources)} 个香港频道")
            return len(sources)
        return 0
    
    def sort_sources(self, sources):
        """按照分类优先级和频道名称排序"""
        # 创建分类索引映射
        category_index = {category: idx for idx, category in enumerate(self.category_order)}
        
        # 对不在预定义分类中的频道，给一个很大的索引值，使其排在最后
        def get_category_index(category):
            return category_index.get(category, len(self.category_order))
        
        # 按分类优先级和频道名称排序
        return sorted(sources, key=lambda x: (get_category_index(x['category']), x['name']))
    
    def generate_output_files(self, sources):
        """生成输出文件"""
        # 按照分类优先级和频道名称排序
        sorted_sources = self.sort_sources(sources)
        
        # 生成M3U文件
        m3u_content = "#EXTM3U\n"
        for source in sorted_sources:
            m3u_content += f'#EXTINF:-1 tvg-id="{source.get("channel_id", "")}" tvg-name="{source["name"]}" tvg-logo="{source.get("tvg-logo", "")}" group-title="{source["category"]}" tvg-language="{source.get("language", "")}",{source["name"]}\n'
            m3u_content += f'{source["url"]}\n'
        
        with open("hk_tv_sources.m3u", "w", encoding="utf-8") as f:
            f.write(m3u_content)
        
        # 生成TXT文件
        txt_content = "# 香港电视直播源\n"
        txt_content += f"# 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        txt_content += "# 来源: 多个公开直播源仓库\n"
        if self.custom_sources:
            txt_content += "# 包含自定义源\n"
        txt_content += "# 此文件由GitHub Actions自动生成，每2天更新一次\n"
        txt_content += "# 已通过连接测试，响应时间越短的源越稳定\n\n"
        
        # 按分类组织频道
        categories = {}
        for source in sorted_sources:
            category = source["category"]
            if category not in categories:
                categories[category] = []
            categories[category].append(source)
        
        # 按分类优先级排序
        sorted_categories = sorted(categories.items(), key=lambda x: self.category_order.index(x[0]) if x[0] in self.category_order else len(self.category_order))
        
        # 按分类输出
        for category, channels in sorted_categories:
            txt_content += f"\n# {category}\n"
            for channel in channels:
                hd_flag = "[HD]" if channel.get('hd') else ""
                response_time = channel.get('response_time', 9999)
                time_info = f"[{response_time}ms]" if response_time < 9999 else "[超时]"
                txt_content += f"{channel['name']}{hd_flag}{time_info},{channel['url']}\n"
        
        with open("hk_tv_sources.txt", "w", encoding="utf-8") as f:
            f.write(txt_content)
        
        print(f"已生成 hk_tv_sources.m3u 和 hk_tv_sources.txt")
        print(f"M3U文件包含 {len(sources)} 个频道")

def main():
    """主函数"""
    fetcher = HKTVSourceFetcher()
    sources = fetcher.fetch_all_sources()
    
    # 如果没有获取到任何源，尝试使用缓存或已知稳定源
    if not sources:
        print("使用备用方案...")
        # 检查是否有之前的缓存文件
        if os.path.exists("hk_tv_sources_backup.m3u"):
            print("从缓存文件加载备用源...")
            with open("hk_tv_sources_backup.m3u", "r", encoding="utf-8") as f:
                content = f.read()
            sources = fetcher.parse_m3u_content(content, "缓存备份")
        else:
            # 使用一些相对稳定的公开源作为最终备用
            backup_urls = [
                "https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/ipv6.m3u",
                "https://iptv-org.github.io/iptv/countries/hk.m3u"
            ]
            for url in backup_urls:
                content = fetcher.make_request(url)
                if content:
                    sources = fetcher.parse_m3u_content(content, "最终备用")
                    break
    
    # 生成输出文件
    if sources:
        # 增强元数据
        enhanced_sources = fetcher.enhance_metadata(sources)
        # 测试连接
        tested_sources = fetcher.test_sources_connectivity(enhanced_sources)
        fetcher.generate_output_files(tested_sources)
        
        # 保存一份备份供下次使用
        with open("hk_tv_sources_backup.m3u", "w", encoding="utf-8") as f:
            f.write("#EXTM3U\n")
            for source in tested_sources:
                f.write(f"#EXTINF:-1 tvg-id=\"{source.get('channel_id', '')}\" group-title=\"{source['category']}\",{source['name']}\n")
                f.write(f"{source['url']}\n")
    else:
        print("无法获取任何直播源，请检查网络连接")

if __name__ == "__main__":
    main()
