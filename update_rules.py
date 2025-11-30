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
    "perplexity",
    "grok",
    "x.com",      # X (Twitter)
    "x.ai",       # Grok 相關
    "twitter",
    "huggingface",
    "anthropic",  # Claude
    "poe"         # Poe
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
    # --- 修改處：檔案名稱變更為 ai_ad.conf ---
    conf_file = "ai_ad.conf"
    header = ""
    
    # 1. 讀取並保留 [General] 設定
    if os.path.exists(conf_file):
        with open(conf_file, "r", encoding="utf-8") as f:
            content = f.read()
            if "[Rule]" in content:
                header = content.split("[Rule]")[0]
            else:
                header = content
                if "[General]" not in header:
                    header = "[General]\nbypass-system = true\n\n"
    else:
        print(f"{conf_file} not found, creating new header.")
        header = "[General]\nbypass-system = true\n\n"

    # 2. 下載並解析規則
    ai_rules = fetch_and_parse(urls["AI"]["url"], urls["AI"]["policy"], exclusions=AI_EXCLUSIONS)
    ads_rules = fetch_and_parse(urls["Ads"]["url"], urls["Ads"]["policy"])

    # 3. 組合新內容 (AI 在前，Ads 在後)
    new_content = header.strip() + "\n\n"
    new_content += f"# Updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    new_content += "[Rule]\n"
    
    # AI (Proxy)
    new_content += f"# --- Category: AI (Proxy) [{len(ai_rules)}] ---\n"
    new_content += "\n".join(ai_rules) + "\n\n"
    
    # Ads (Reject)
    new_content += f"# --- Category: Ads (Reject) [{len(ads_rules)}] ---\n"
    new_content += "\n".join(ads_rules) + "\n"

    # 兜底規則
    new_content += "\n# Final Match\n"
    new_content += "FINAL,DIRECT\n" 

    # 4. 寫入檔案
    with open(conf_file, "w", encoding="utf-8") as f:
        f.write(new_content)
    
    print(f"Successfully updated {conf_file}")

if __name__ == "__main__":
    main()
