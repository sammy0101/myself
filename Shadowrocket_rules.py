import requests
import datetime
import os

# 設定來源網址
urls = {
    "Ads": {
        "url": "https://github.com/MetaCubeX/meta-rules-dat/raw/refs/heads/meta/geo/geosite/category-ads-all.list",
        "policy": "Reject"
    },
    "AI": {
        "url": "https://github.com/MetaCubeX/meta-rules-dat/raw/refs/heads/meta/geo/geosite/category-ai-!cn.list",
        "policy": "Proxy"
    }
}

# 設定要從 AI 代理列表中剔除的關鍵字 (香港可直連的網站)
AI_EXCLUSIONS = [
    "x.com",             # X (Twitter)
    "x.ai",              # Grok 相關
    "anthropic",         # Claude
    "poe.com",           # Poe (香港可直連)
    "poecdn",            # Poe CDN
    "perplexity",        # Perplexity (香港可直連)
    "bing.com",          # Bing / Copilot (香港可直連)
    "bing.net",
    "copilot",           # Microsoft Copilot
    "huggingface.co"     # HuggingFace
]

def fetch_and_parse(url, policy, exclusions=None):
    rules = []
    if exclusions is None:
        exclusions = []
        
    try:
        print(f"Downloading {url}...")
        resp = requests.get(url)
        resp.raise_for_status()
        lines = resp.text.splitlines()
        
        for line in lines:
            line = line.strip()
            # 跳過空行或註解
            if not line or line.startswith("#"):
                continue
            
            # 處理域名 (MetaCubeX 格式可能是 +.domain 或 domain)
            domain = line.replace("+.", "").strip()
            
            if not domain:
                continue

            # --- 過濾邏輯 ---
            is_excluded = False
            for kw in exclusions:
                if kw.lower() in domain.lower():
                    is_excluded = True
                    break
            
            if is_excluded:
                continue
            # ----------------
            
            rules.append(f"DOMAIN-SUFFIX,{domain},{policy}")
            
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return rules

def main():
    conf_file = "ai_ad.conf"
    header_content = ""
    
    # 1. 讀取並保留 [General] 設定，同時清理舊的 Update 時間戳
    if os.path.exists(conf_file):
        try:
            with open(conf_file, "r", encoding="utf-8") as f:
                content = f.read()
                
                # 根據 [Rule] 切割，只保留前半部分 (Header)
                if "[Rule]" in content:
                    raw_header = content.split("[Rule]")[0]
                else:
                    raw_header = content
                
                # --- 關鍵修復：清理舊的時間戳 ---
                clean_lines = []
                for line in raw_header.splitlines():
                    # 如果這一行不是以 "# Updated:" 開頭，則保留
                    if not line.strip().startswith("# Updated:"):
                        clean_lines.append(line)
                
                header_content = "\n".join(clean_lines)
        except Exception as e:
            print(f"讀取舊設定檔時發生錯誤: {e}, 將使用預設 Header")
            header_content = ""
    
    # 如果沒有 Header 或檔案不存在，給予預設值
    if not header_content or "[General]" not in header_content:
        if "[General]" not in header_content:
            print("Header not found or incomplete, adding default [General].")
            header_content = "[General]\nbypass-system = true\n" + header_content

    # 2. 下載並解析規則
    ai_rules = fetch_and_parse(urls["AI"]["url"], urls["AI"]["policy"], exclusions=AI_EXCLUSIONS)
    ads_rules = fetch_and_parse(urls["Ads"]["url"], urls["Ads"]["policy"])

    # 3. 組合新內容
    # Header
    new_content = header_content.strip() + "\n\n"
    
    # 插入唯一的最新時間戳
    current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    new_content += f"# Updated: {current_time}\n"
    
    # 開始規則區段
    new_content += "[Rule]\n"
    
    # AI (Proxy)
    new_content += f"# --- Category: AI (Proxy) [{len(ai_rules)}] ---\n"
    new_content += "\n".join(ai_rules) + "\n\n"
    
    # Ads (Reject)
    new_content += f"# --- Category: Ads (Reject) [{len(ads_rules)}] ---\n"
    new_content += "\n".join(ads_rules) + "\n"

    # 兜底規則 (可選，如果您希望最後一條是 DIRECT)
    new_content += "\n# Final Match\n"
    new_content += "FINAL,DIRECT\n" 

    # 4. 寫入檔案
    with open(conf_file, "w", encoding="utf-8") as f:
        f.write(new_content)
    
    print(f"Successfully updated {conf_file} with timestamp: {current_time}")

if __name__ == "__main__":
    main()
