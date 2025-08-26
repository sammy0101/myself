# scripts/fetch_hk_tv_sources.py
import requests
import re
import time
import json
import os
import socket
import hashlib
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional, Tuple

# --- 全域設定 ---
# 將常數集中管理，方便修改
CONFIG = {
    "TIMEOUT": 10,
    "CONNECTIVITY_TIMEOUT": 5,
    "MAX_WORKERS": 10,
    "CACHE_DIR": "cache",
    "CACHE_EXPIRATION": 3600,  # 1 小時
    "CUSTOM_SOURCES_FILE": "custom_sources.txt",
    "OUTPUT_M3U_FILE": "hk_tv_sources.m3u",
    "OUTPUT_TXT_FILE": "hk_tv_sources.txt",
    "BACKUP_M3U_FILE": "hk_tv_sources_backup.m3u",
    "USER_AGENT": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

# 設定日誌記錄
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class HKTVSourceFetcher:
    def __init__(self):
        self.sources: List[Dict[str, Any]] = []
        self.headers = {'User-Agent': CONFIG["USER_AGENT"]}
        
        # 將靜態資料移出 __init__，使其成為類別屬性，避免每次實例化都重新定義
        self.category_order = [
            'TVB', 'ViuTV', 'HOY TV', 'RTHK', '新闻', '体育', '电影', '国际', '儿童', '其他'
        ]
        self.channel_categories = {
            'TVB': ['TVB', '無綫', '无线', '翡翠', '明珠', 'J2'],
            'ViuTV': ['ViuTV', 'Viu'],
            'HOY TV': ['HOY', '開電視', '开电视', '有線', '有线', '奇妙', '77台', '78台'],
            'RTHK': ['RTHK', '香港电台', '港台'],
            '新闻': ['新聞', '新闻', 'NEWS', '資訊', '財經', '财经'],
            '体育': ['體育', '体育', 'SPORTS', '賽馬', '赛马'],
            '电影': ['電影', '电影', 'MOVIE', '影院', '戲劇', '戏剧'],
            '国际': ['國際', '国际', 'WORLD', 'BBC', 'CNN', '凤凰衛視', '鳳凰衛視'],
            '儿童': ['兒童', '儿童', 'KIDS', '卡通', '動畫', '动画'],
        }
        self.hk_keywords = [
            '香港', 'HK', 'TVB', '翡翠', '明珠', 'ViuTV', 'RTHK', '鳳凰', 
            '開電視', '开电视', 'HOY', '有線', '有线', '奇妙', '77台', '78台', '港台',
            '澳門', 'Macau', '澳视'
        ]
        
        self.custom_sources = self._load_custom_sources()

    def _load_custom_sources(self) -> List[Dict[str, Any]]:
        """從 custom_sources.txt 檔案載入自訂來源 (私有方法)"""
        custom_sources = []
        custom_file = CONFIG["CUSTOM_SOURCES_FILE"]
        
        if not os.path.exists(custom_file):
            logging.info(f"自訂來源檔案 '{custom_file}' 不存在，跳過載入。")
            return custom_sources

        try:
            with open(custom_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    parsed_url = urlparse(line)
                    name = f"自定义源_{parsed_url.netloc}"
                    custom_sources.append({"name": name, "url": line})
        except Exception as e:
            logging.error(f"讀取自訂來源檔案時出錯: {e}")
        
        logging.info(f"從自訂檔案載入了 {len(custom_sources)} 個來源")
        return custom_sources

    def _make_request(self, url: str, use_cache: bool = True) -> Optional[str]:
        """通用請求函數，支援快取 (私有方法)"""
        os.makedirs(CONFIG["CACHE_DIR"], exist_ok=True)
        url_hash = hashlib.md5(url.encode()).hexdigest()
        cache_file = os.path.join(CONFIG["CACHE_DIR"], f"{url_hash}.cache")
        
        if use_cache and os.path.exists(cache_file):
            if (time.time() - os.path.getmtime(cache_file)) < CONFIG["CACHE_EXPIRATION"]:
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        return f.read()
                except Exception as e:
                    logging.warning(f"讀取快取檔案失敗: {e}")

        try:
            response = requests.get(url, timeout=CONFIG["TIMEOUT"], headers=self.headers)
            response.raise_for_status()  # 如果狀態碼不是 2xx，則引發 HTTPError
            content = response.text
            try:
                with open(cache_file, 'w', encoding='utf-8') as f:
                    f.write(content)
            except Exception as e:
                logging.warning(f"寫入快取檔案失敗: {e}")
            return content
        except requests.RequestException as e:
            logging.error(f"請求失敗 {url}: {e}")
        return None

    def _is_hk_channel(self, name: str, group: str) -> bool:
        """判斷是否為香港頻道 (私有方法)"""
        text_to_check = (name + group).upper()
        return any(keyword.upper() in text_to_check for keyword in self.hk_keywords)

    def _parse_m3u_content(self, content: str, source_name: str, filter_hk: bool = True) -> List[Dict[str, Any]]:
        """解析 M3U 內容 (私有方法)"""
        sources = []
        if not content:
            return sources

        # 優化正則表達式，一次性捕獲所有資訊
        pattern = re.compile(r'#EXTINF:-1([^,]*),(.*?)\n(http[^\s]*)')
        matches = pattern.findall(content)

        for params_str, name, url in matches:
            params = dict(re.findall(r'(\S+?)="([^"]*)"', params_str))
            group = params.get('group-title', source_name)
            
            if not filter_hk or self._is_hk_channel(name, group):
                sources.append({
                    "name": name.strip(),
                    "url": url.strip(),
                    "group": group,
                    "source": source_name,
                    "params": params
                })
        return sources

    def _fetch_from_source(self, url: str, name: str, filter_hk: bool = True):
        """從單一來源獲取並解析內容"""
        logging.info(f"開始從 {name} 獲取...")
        content = self._make_request(url)
        if content:
            sources = self._parse_m3u_content(content, name, filter_hk=filter_hk)
            self.sources.extend(sources)
            logging.info(f"從 {name} 獲取到 {len(sources)} 個相關頻道")
        else:
            logging.warning(f"從 {name} 未獲取到任何內容")

    def fetch_all_sources(self):
        """從所有可用來源並行獲取直播源"""
        logging.info("開始獲取香港電視直播源...")
        
        # 來源列表化，更易於管理
        default_sources = [
            {"url": "https://live.fanmingming.com/tv/m3u/ipv6.m3u", "name": "范明明IPv6"},
            {"url": "https://raw.githubusercontent.com/fanmingming/live/main/tv/m3u/v6.m3u", "name": "范明明v6"},
            {"url": "https://iptv-org.github.io/iptv/countries/hk.m3u", "name": "iptv-org", "filter_hk": False},
            {"url": "https://epg.pw/test_channels_hong_kong.m3u", "name": "epg.pw", "filter_hk": False},
            {"url": "https://aktv.space/live.m3u", "name": "AKTV"},
            {"url": "https://raw.githubusercontent.com/YueChan/Live/main/IPTV.m3u", "name": "YueChan"},
            {"url": "https://raw.githubusercontent.com/BigBigGrandG/IPTV-URL/release/Gather.m3u", "name": "BigBigGrandG"}
        ]

        # 合併預設來源和自訂來源
        all_source_configs = default_sources + self.custom_sources

        with ThreadPoolExecutor(max_workers=CONFIG["MAX_WORKERS"]) as executor:
            futures = [
                executor.submit(
                    self._fetch_from_source,
                    src['url'],
                    src['name'],
                    src.get('filter_hk', True)
                ) for src in all_source_configs
            ]
            for future in as_completed(futures):
                try:
                    future.result()  # 獲取結果以觸發異常
                except Exception as e:
                    logging.error(f"獲取來源時發生錯誤: {e}")
        
        unique_sources = self._remove_duplicates()
        enhanced_sources = self._enhance_metadata(unique_sources)
        logging.info(f"總共獲取到 {len(enhanced_sources)} 個唯一的香港頻道")
        
        tested_sources = self._test_sources_connectivity(enhanced_sources)
        logging.info(f"連接測試後剩餘 {len(tested_sources)} 個有效頻道")

        self._generate_output_files(tested_sources)
        return tested_sources

    def _remove_duplicates(self) -> List[Dict[str, Any]]:
        """去重處理，使用 URL 作為唯一標識"""
        unique_sources = {}
        for source in self.sources:
            # 以標準化的 URL 作為鍵，避免重複
            normalized_url = source['url'].split('?')[0].rstrip('/')
            if normalized_url not in unique_sources:
                unique_sources[normalized_url] = source
        return list(unique_sources.values())

    def _determine_category(self, name: str, group: str) -> str:
        """確定頻道分類"""
        text_to_check = (name + group).upper()
        for category, keywords in self.channel_categories.items():
            if any(keyword.upper() in text_to_check for keyword in keywords):
                return category
        return '其他'

    def _determine_resolution(self, name: str) -> str:
        """從名稱中確定清晰度"""
        name_upper = name.upper()
        if '4K' in name_upper or 'UHD' in name_upper: return '4K'
        if '1080' in name_upper or 'FHD' in name_upper: return '1080p'
        if '720' in name_upper or 'HD' in name_upper: return '720p'
        if '480' in name_upper or 'SD' in name_upper: return '480p'
        return '未知'

    def _enhance_metadata(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """增強頻道元資料"""
        for source in sources:
            name = source['name']
            group = source.get('group', '')
            source['category'] = self._determine_category(name, group)
            source['resolution'] = self._determine_resolution(name)
        return sources

    def _test_source_connectivity(self, source: Dict[str, Any]) -> Tuple[bool, int, str]:
        """測試單一來源的連接性"""
        url = source['url']
        try:
            start_time = time.time()
            with requests.get(url, stream=True, timeout=CONFIG["CONNECTIVITY_TIMEOUT"], headers=self.headers) as response:
                response.raise_for_status()
                # 檢查是否有內容返回
                first_chunk = next(response.iter_content(chunk_size=512), None)
                if first_chunk:
                    response_time = int((time.time() - start_time) * 1000)
                    return True, response_time, "成功"
                else:
                    return False, 9999, "無內容"
        except requests.exceptions.Timeout:
            return False, 9999, "連接逾時"
        except requests.exceptions.RequestException as e:
            # 簡化錯誤訊息
            error_msg = str(e).split('\n')[0]
            return False, 9999, f"請求錯誤: {error_msg[:50]}"
        except Exception:
            return False, 9999, "未知錯誤"

    def _test_sources_connectivity(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """並行測試來源的連接性並過濾無效來源"""
        logging.info("開始測試頻道連接性...")
        valid_sources = []
        
        with ThreadPoolExecutor(max_workers=CONFIG["MAX_WORKERS"] * 2) as executor: # 測試可以開更多執行緒
            future_to_source = {executor.submit(self._test_source_connectivity, source): source for source in sources}
            
            total = len(sources)
            for i, future in enumerate(as_completed(future_to_source), 1):
                source = future_to_source[future]
                try:
                    is_valid, response_time, status = future.result()
                    if is_valid:
                        source['response_time'] = response_time
                        valid_sources.append(source)
                        logging.info(f"[{i}/{total}] ✓ {source['name']} - {response_time}ms")
                    else:
                        logging.warning(f"[{i}/{total}] ✗ {source['name']} - {status}")
                except Exception as e:
                    logging.error(f"[{i}/{total}] ✗ {source['name']} - 測試時發生嚴重錯誤: {e}")
        
        return valid_sources
    
    def _sort_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """按照分類優先級和頻道名稱排序"""
        category_index = {category: idx for idx, category in enumerate(self.category_order)}
        
        def sort_key(source):
            cat = source['category']
            return (category_index.get(cat, len(self.category_order)), source['name'])
            
        return sorted(sources, key=sort_key)

    def _generate_output_files(self, sources: List[Dict[str, Any]]):
        """生成輸出檔案"""
        if not sources:
            logging.warning("沒有有效的來源可供生成檔案。")
            return

        sorted_sources = self._sort_sources(sources)
        
        # --- 生成 M3U 檔案 ---
        m3u_lines = ["#EXTM3U"]
        for source in sorted_sources:
            params = source.get("params", {})
            m3u_lines.append(
                f'#EXTINF:-1 tvg-id="{params.get("tvg-id", "")}" '
                f'tvg-name="{source["name"]}" '
                f'tvg-logo="{params.get("tvg-logo", "")}" '
                f'group-title="{source["category"]}",{source["name"]}'
            )
            m3u_lines.append(source["url"])
        
        with open(CONFIG["OUTPUT_M3U_FILE"], "w", encoding="utf-8") as f:
            f.write("\n".join(m3u_lines))
        
        # --- 生成 TXT 檔案 ---
        txt_lines = [
            f"# 香港電視直播源",
            f"# 更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ]
        
        channels_by_category = {}
        for source in sorted_sources:
            cat = source['category']
            if cat not in channels_by_category:
                channels_by_category[cat] = []
            channels_by_category[cat].append(source)
        
        for category in self.category_order:
            if category in channels_by_category:
                txt_lines.append(f"\n# {category}")
                for channel in channels_by_category[category]:
                    hd_flag = "[HD]" if channel['resolution'] in ['1080p', '720p'] else ""
                    time_info = f"[{channel.get('response_time', 'N/A')}ms]"
                    txt_lines.append(f"{channel['name']}{hd_flag}{time_info},{channel['url']}")
        
        with open(CONFIG["OUTPUT_TXT_FILE"], "w", encoding="utf-8") as f:
            f.write("\n".join(txt_lines))
        
        logging.info(f"已生成 {CONFIG['OUTPUT_M3U_FILE']} 和 {CONFIG['OUTPUT_TXT_FILE']}")
        
        # --- 備份一份供下次使用 ---
        with open(CONFIG["BACKUP_M3U_FILE"], "w", encoding="utf-8") as f:
             f.write("\n".join(m3u_lines))

def main():
    """主函數"""
    fetcher = HKTVSourceFetcher()
    valid_sources = fetcher.fetch_all_sources()
    
    if not valid_sources:
        logging.warning("未能從網路獲取任何有效來源，嘗試從備份檔案恢復。")
        backup_file = CONFIG["BACKUP_M3U_FILE"]
        if os.path.exists(backup_file):
            with open(backup_file, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 重新處理備份檔案
            sources = fetcher._parse_m3u_content(content, "備份", filter_hk=False)
            enhanced = fetcher._enhance_metadata(sources)
            fetcher._generate_output_files(enhanced) # 直接用備份生成，不再測試
            logging.info(f"已從 {backup_file} 成功恢復並生成檔案。")
        else:
            logging.error("無法獲取任何直播源，且備份檔案不存在，請檢查網路連線或來源設定。")

if __name__ == "__main__":
    main()
