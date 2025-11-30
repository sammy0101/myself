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

def fetch_and_parse(url, policy):
    rules = []
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
            
            # MetaCubeX 規則通常是 domain.com 或 +.domain.com
            # Shadowrocket 使用 DOMAIN-SUFFIX 可以涵蓋子域名
            domain = line.replace("+.", "").strip()
            
            # 避免重複或無效域名
            if domain:
                rules.append(f"DOMAIN-SUFFIX,{domain},{policy}")
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return rules

def main():
    # 1. 讀取現有的 Ai.conf 以保留 [General] 設定
    conf_file = "Ai.conf"
    header = ""
    
    if os.path.exists(conf_file):
        with open(conf_file, "r", encoding="utf-8") as f:
            content = f.read()
            # 分割出 [General] 部分，假設 [Rule] 是分隔點
            if "[Rule]" in content:
                header = content.split("[Rule]")[0]
            else:
                # 如果找不到 [Rule]，嘗試只保留 header，或者預設一個
                header = content
                # 如果檔案是空的或格式不對，給一個基本 header
                if "[General]" not in header:
                    header = "[General]\nbypass-system = true\n\n"
    else:
        print("Ai.conf not found, creating new header.")
        header = "[General]\nbypass-system = true\n\n"

    # 2. 獲取並轉換規則
    # 建議順序：先 Reject (廣告)，再 Proxy (AI)，最後是漏網之魚的處理
    ads_rules = fetch_and_parse(urls["Ads"]["url"], urls["Ads"]["policy"])
    ai_rules = fetch_and_parse(urls["AI"]["url"], urls["AI"]["policy"])

    # 3. 組合新內容
    new_content = header.strip() + "\n\n"
    new_content += f"# Updated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    new_content += "[Rule]\n"
    
    new_content += f"# --- Category: Ads ({len(ads_rules)}) ---\n"
    new_content += "\n".join(ads_rules) + "\n"
    
    new_content += f"# --- Category: AI ({len(ai_rules)}) ---\n"
    new_content += "\n".join(ai_rules) + "\n"

    # 加入最後的兜底規則 (可選，視你的需求保留或修改)
    new_content += "\n# Final Match\n"
    new_content += "FINAL,DIRECT\n"
    new_content += "GEOIP,CN,DIRECT\n" # 常見的 Shadowrocket 規則

    # 4. 寫入檔案
    with open(conf_file, "w", encoding="utf-8") as f:
        f.write(new_content)
    
    print(f"Successfully updated {conf_file}")

if __name__ == "__main__":
    main()
