# scripts/fetch_hk_tv_sources.py
import requests
import re
import time
import os
import hashlib
import logging
import m3u8
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError
from urllib.parse import urlparse
from typing import List, Dict, Any, Optional, Tuple
from pebble import ProcessPool

# --- 全域設定 ---
CONFIG = {
    "TIMEOUT": 10,
    "MAX_WORKERS": 20,
    "CACHE_DIR": "cache",
    "CACHE_EXPIRATION": 3600,
    "CUSTOM_SOURCES_FILE": "custom_sources.txt",
    "OUTPUT_M3U_FILE": "hk_tv_sources.m3u",
    "OUTPUT_TXT_FILE": "hk_tv_sources.txt",
    "BACKUP_M3U_FILE": "hk_tv_sources_backup.m3u",
    "USER_AGENT": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    "TASK_TIMEOUT": 15
}

# 設定日誌記錄
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def run_connectivity_test(source: Dict[str, Any]) -> Tuple[bool, int, str]:
    url = source['url']
    start_time = time.time()
    headers = {'User-Agent': CONFIG["USER_AGENT"]}
    robust_timeout = (3.05, 5)
    try:
        with requests.get(url, stream=True, timeout=robust_timeout, headers=headers) as response:
            response.raise_for_status()
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text/html' in content_type:
                return False, 9999, "無效內容 (HTML)"
            content = response.text
            try:
                playlist = m3u8.loads(content, uri=url)
                if playlist.is_variant:
                    if not playlist.playlists: return False, 9999, "M3U8無效 (無子播放列表)"
                    uri_to_test = playlist.playlists[0].uri
                elif playlist.segments:
                    uri_to_test = playlist.segments[0].uri
                else:
                    return False, 9999, "M3U8無效 (空播放列表)"
                seg_response = requests.head(uri_to_test, timeout=robust_timeout, headers=headers)
                seg_response.raise_for_status()
                response_time = int((time.time() - start_time) * 1000)
                return True, response_time, "驗證成功"
            except Exception:
                if response.status_code == 200 and len(content) > 0:
                    response_time = int((time.time() - start_time) * 1000)
                    return True, response_time, "成功 (直接串流)"
                return False, 9999, "M3U8解析失敗"
    except requests.exceptions.Timeout:
        return False, 9999, "連接逾時"
    except requests.exceptions.RequestException as e:
        return False, 9999, f"請求錯誤: {str(e).splitlines()[0][:50]}"
    except Exception as e:
        return False, 9999, f"未知錯誤: {str(e)[:50]}"

class HKTVSourceFetcher:
    def __init__(self):
        self.sources: List[Dict[str, Any]] = []
        self.headers = {'User-Agent': CONFIG["USER_AGENT"]}
        self.category_order = ['TVB', 'ViuTV', 'HOY TV', 'RTHK', '新闻', '体育', '电影', '国际', '儿童', '其他']
        self.channel_categories = {
            'TVB': ['TVB', '無綫', '無線', '翡翠', '明珠', 'J2'], 'ViuTV': ['ViuTV', 'Viu'],
            'HOY TV': ['HOY', '開電視', '开电视', '有線', '有线', '奇妙', '77台', '78台'], 'RTHK': ['RTHK', '香港电台', '港台'],
            '新闻': ['新聞', '新闻', 'NEWS', '資訊', '財經', '财经'], '体育': ['體育', '体育', 'SPORTS', '賽馬', '赛马'],
            '电影': ['電影', '电影', 'MOVIE', '影院', '戲劇', '戏剧'], '国际': ['國際', '国际', 'WORLD', 'BBC', 'CNN', '凤凰衛視', '鳳凰衛視'],
            '儿童': ['兒童', '儿童', 'KIDS', '卡通', '動畫', '动画'],
        }
        self.hk_keywords = ['香港', 'HK', 'TVB', '翡翠', '明珠', 'ViuTV', 'RTHK', '鳳凰', '開電視', '开电视', 'HOY', '有線', '有线', '奇妙', '77台', '78台', '港台', '澳門', 'Macau', '澳视']
        self.custom_sources = self._load_custom_sources()

    def _load_custom_sources(self) -> List[Dict[str, Any]]:
        custom_sources = []
        custom_file = CONFIG["CUSTOM_SOURCES_FILE"]
        if not os.path.exists(custom_file):
            logging.warning(f"自訂來源檔案 '{custom_file}' 不存在，跳過載入。")
            return custom_sources
        try:
            with open(custom_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'): continue
                    parsed_url = urlparse(line)
                    name = f"CustomSource-{parsed_url.netloc}"
                    custom_sources.append({"url": line, "name": name, "filter_hk": True})
        except Exception as e:
            logging.error(f"讀取自訂來源檔案時出錯: {e}")
        logging.info(f"從自訂檔案載入了 {len(custom_sources)} 個來源")
        return custom_sources

    def _make_request(self, url: str, use_cache: bool = True) -> Optional[str]:
        os.makedirs(CONFIG["CACHE_DIR"], exist_ok=True)
        url_hash = hashlib.md5(url.encode()).hexdigest()
        cache_file = os.path.join(CONFIG["CACHE_DIR"], f"{url_hash}.cache")
        if use_cache and os.path.exists(cache_file):
            if (time.time() - os.path.getmtime(cache_file)) < CONFIG["CACHE_EXPIRATION"]:
                try:
                    with open(cache_file, 'r', encoding='utf-8') as f: return f.read()
                except Exception as e:
                    logging.warning(f"讀取快取檔案失敗: {e}")
        try:
            response = requests.get(url, timeout=CONFIG["TIMEOUT"], headers=self.headers)
            response.raise_for_status()
            content = response.text
            try:
                with open(cache_file, 'w', encoding='utf-8') as f: f.write(content)
            except Exception as e:
                logging.warning(f"寫入快取檔案失敗: {e}")
            return content
        except requests.RequestException as e:
            logging.error(f"請求失敗 {url}: {e}")
        return None

    def _is_hk_channel(self, name: str, group: str) -> bool:
        text_to_check = (name + group).upper()
        return any(keyword.upper() in text_to_check for keyword in self.hk_keywords)

    def _parse_m3u_content(self, content: str, source_name: str, filter_hk: bool = True) -> List[Dict[str, Any]]:
        sources = []
        if not content: return sources
        pattern = re.compile(r'#EXTINF:-1([^,]*),(.*?)\n(http[^\s]*)')
        matches = pattern.findall(content)
        for params_str, name, url in matches:
            params = dict(re.findall(r'(\S+?)="([^"]*)"', params_str))
            group = params.get('group-title', source_name)
            if not filter_hk or self._is_hk_channel(name, group):
                sources.append({"name": name.strip(), "url": url.strip(), "group": group, "source": source_name, "params": params})
        return sources

    def _fetch_from_source(self, url: str, name: str, filter_hk: bool = True):
        logging.info(f"開始從 {name} ({url}) 獲取...")
        content = self._make_request(url)
        if content:
            sources = self._parse_m3u_content(content, name, filter_hk=filter_hk)
            self.sources.extend(sources)
            logging.info(f"從 {name} 獲取到 {len(sources)} 個相關頻道")
        else:
            logging.warning(f"從 {name} 未獲取到任何內容")
    
    def fetch_all_sources(self):
        logging.info(f"開始從 {CONFIG['CUSTOM_SOURCES_FILE']} 獲取所有直播源...")
        all_source_configs = self.custom_sources
        if not all_source_configs:
            logging.warning(f"{CONFIG['CUSTOM_SOURCES_FILE']} 為空或不存在，沒有可獲取的來源。")
            return []
        with ThreadPoolExecutor(max_workers=CONFIG["MAX_WORKERS"]) as executor:
            futures = [executor.submit(self._fetch_from_source, src['url'], src['name'], src.get('filter_hk', True)) for src in all_source_configs]
            for future in as_completed(futures):
                try: future.result()
                except Exception as e: logging.error(f"獲取來源時發生錯誤: {e}")
        
        unique_sources = self._remove_duplicates()
        enhanced_sources = self._enhance_metadata(unique_sources)
        logging.info(f"總共獲取到 {len(enhanced_sources)} 個唯一的香港頻道")
        
        tested_sources = self._test_sources_connectivity_with_pebble(enhanced_sources)
        logging.info(f"連接測試後剩餘 {len(tested_sources)} 個有效頻道")
        self._generate_output_files(tested_sources)
        return tested_sources

    def _test_sources_connectivity_with_pebble(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        logging.info("開始深度測試頻道連接性 (使用 PebblePool，可強制超時)...")
        valid_sources = []
        with ProcessPool(max_workers=CONFIG["MAX_WORKERS"]) as pool:
            # --- ↓↓↓ 這就是之前出錯的那一行，現已修正 ↓↓↓ ---
            future_map = {pool.schedule(run_connectivity_test, args=(source,), timeout=CONFIG["TASK_TIMEOUT"]): source for source in sources}
            # --- ↑↑↑ 修正結束 ↑↑↑ ---
            total = len(sources)
            for i, future in enumerate(as_completed(future_map), 1):
                source = future_map[future]
                try:
                    is_valid, response_time, status = future.result()
                    if is_valid:
                        source['response_time'] = response_time
                        valid_sources.append(source)
                        logging.info(f"[{i}/{total}] ✓ {source['name']} - {response_time}ms ({status})")
                    else:
                        logging.warning(f"[{i}/{total}] ✗ {source['name']} - {status}")
                except TimeoutError:
                    logging.warning(f"[{i}/{total}] ✗ {source['name']} - 測試嚴重逾時 (>{CONFIG['TASK_TIMEOUT']}s)，已被終止")
                except Exception as e:
                    logging.error(f"[{i}/{total}] ✗ {source['name']} - 測試時發生嚴重錯誤: {e}")
        return valid_sources
    
    def _remove_duplicates(self) -> List[Dict[str, Any]]:
        unique_sources = {}
        for source in self.sources:
            normalized_url = source['url'].split('?')[0].rstrip('/')
            if normalized_url not in unique_sources:
                unique_sources[normalized_url] = source
        return list(unique_sources.values())

    def _determine_category(self, name: str, group: str) -> str:
        text_to_check = (name + group).upper()
        for category, keywords in self.channel_categories.items():
            if any(keyword.upper() in text_to_check for keyword in keywords):
                return category
        return '其他'

    def _determine_resolution(self, name: str) -> str:
        name_upper = name.upper()
        if '4K' in name_upper or 'UHD' in name_upper: return '4K'
        if '1080' in name_upper or 'FHD' in name_upper: return '1080p'
        if '720' in name_upper or 'HD' in name_upper: return '720p'
        if '480' in name_upper or 'SD' in name_upper: return '4-80p'
        return '未知'

    def _enhance_metadata(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for source in sources:
            name = source['name']
            group = source.get('group', '')
            source['category'] = self._determine_category(name, group)
            source['resolution'] = self._determine_resolution(name)
        return sources
        
    def _sort_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        category_index = {category: idx for idx, category in enumerate(self.category_order)}
        def sort_key(source):
            cat = source['category']
            return (category_index.get(cat, len(self.category_order)), source['name'])
        return sorted(sources, key=sort_key)

    def _generate_output_files(self, sources: List[Dict[str, Any]]):
        if not sources:
            logging.warning("沒有有效的來源可供生成檔案。")
            return
        sorted_sources = self._sort_sources(sources)
        m3u_lines = ["#EXTM3U"]
        for source in sorted_sources:
            params = source.get("params", {})
            m3u_lines.append(f'#EXTINF:-1 tvg-id="{params.get("tvg-id", "")}" tvg-name="{source["name"]}" tvg-logo="{params.get("tvg-logo", "")}" group-title="{source["category"]}",{source["name"]}')
            m3u_lines.append(source["url"])
        with open(CONFIG["OUTPUT_M3U_FILE"], "w", encoding="utf-8") as f: f.write("\n".join(m3u_lines))
        txt_lines = [f"# 香港電視直播源", f"# 更新時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"]
        channels_by_category = {}
        for source in sorted_sources:
            cat = source['category']
            channels_by_category.setdefault(cat, []).append(source)
        for category in self.category_order:
            if category in channels_by_category:
                txt_lines.append(f"\n# {category}")
                for channel in channels_by_category[category]:
                    hd_flag = "[HD]" if channel['resolution'] in ['1080p', '720p'] else ""
                    time_info = f"[{channel.get('response_time', 'N/A')}ms]"
                    txt_lines.append(f"{channel['name']}{hd_flag}{time_info},{channel['url']}")
        with open(CONFIG["OUTPUT_TXT_FILE"], "w", encoding="utf-8") as f: f.write("\n".join(txt_lines))
        logging.info(f"已生成 {CONFIG['OUTPUT_M3U_FILE']} 和 {CONFIG['OUTPUT_TXT_FILE']}")
        with open(CONFIG["BACKUP_M3U_FILE"], "w", encoding="utf-8") as f: f.write("\n".join(m3u_lines))

def main():
    fetcher = HKTVSourceFetcher()
    valid_sources = fetcher.fetch_all_sources()
    if not valid_sources:
        logging.warning("未能從網路獲取任何有效來源，嘗試從備份檔案恢復。")
        backup_file = CONFIG["BACKUP_M3U_FILE"]
        if os.path.exists(backup_file):
            with open(backup_file, "r", encoding="utf-8") as f: content = f.read()
            sources = fetcher._parse_m3u_content(content, "備份", filter_hk=False)
            enhanced = fetcher._enhance_metadata(sources)
            fetcher._generate_output_files(enhanced)
            logging.info(f"已從 {backup_file} 成功恢復並生成檔案。")
        else:
            logging.error("無法獲取任何直播源，且備份檔案不存在，請檢查網路連線或來源設定。")

if __name__ == "__main__":
    main()
