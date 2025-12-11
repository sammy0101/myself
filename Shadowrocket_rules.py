import requests
import datetime
import os
import re

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
    "cursor.com",
    "cursor.sh",
    "cursorapi.com",
    "cursor-cdn.com",
    "trae.ai",
    "marscode.com",
    "devin.ai",
    "coderabbit.ai",
    "coderabbit.gallery.vsassets.io",
    "mistral.ai",
    "cohere.ai",
    "cohere.com",
    "groq.com",
    "cerebras.ai",
    "openrouter.ai",
    "dify.ai",
    "elevenlabs.com",
    "elevenlabs.io",
    "clipdrop.co",
    "comfy.org",
    "comfyregistry.org",
    "comfyci.org",
    "openart.ai",
    "ciciai.com",
    "cici.com",
    "ciciaicdn.com",
    "coze.com",
    "jasper.ai",
    "dola.com",
    "diabrowser.com",
    "gateway.ai.cloudflare.com",
    "pplx-res.cloudinary.com",
    "browser-intake-datadoghq.com",
    "o33249.ingest.sentry.io",
    "openaiapi-site.azureedge.net",
    "production-openaicom-storage.azureedge.net",
]

def fetch_and_parse(url, policy, exclusions=None):
    rules = []
    if exclusions is None: exclusions = []
    try:
        print(f"Downloading {url}...")
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        lines = resp.text.splitlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"): continue
            domain = line.replace("+.", "").strip()
            if not domain: continue
            
            is_excluded = False
            for kw in exclusions:
                if kw.lower() in domain.lower():
                    is_excluded = True; break
            if is_excluded: continue
            
            rules.append(f"DOMAIN-SUFFIX,{domain},{policy}")
    except Exception as e:
        print(f"Error fetching {url}: {e}")
    return rules

def get_content_without_timestamp(content):
    """移除內容中的 Updated 時間戳以便比對"""
    return re.sub(r'# Updated: .*\n', '', content)

def main():
    conf_file = "ai_ad.conf"
    header_content = ""
    
    # 1. 讀取舊檔案 (如果存在)
    old_content_raw = ""
    if os.path.exists(conf_file):
        try:
            with open(conf_file, "r", encoding="utf-8") as f:
                old_content_raw = f.read()
                
                # 取得 Header
                if "[Rule]" in old_content_raw:
                    raw_header = old_content_raw.split("[Rule]")[0]
                else:
                    raw_header = old_content_raw
                
                # 清理舊 Header 中的時間戳
                clean_lines = [line for line in raw_header.splitlines() if not line.strip().startswith("# Updated:")]
                header_content = "\n".join(clean_lines)
        except Exception:
            header_content = ""

    if not header_content or "[General]" not in header_content:
        if "[General]" not in header_content:
            header_content = "[General]\nbypass-system = true\n" + header_content

    # 2. 下載新規則
    ai_rules = fetch_and_parse(urls["AI"]["url"], urls["AI"]["policy"], exclusions=AI_EXCLUSIONS)
    ads_rules = fetch_and_parse(urls["Ads"]["url"], urls["Ads"]["policy"])

    # 3. 組合新內容 (暫不加時間戳)
    new_body = "[Rule]\n"
    new_body += f"# --- Category: AI (Proxy) [{len(ai_rules)}] ---\n"
    new_body += "\n".join(ai_rules) + "\n\n"
    new_body += f"# --- Category: Ads (Reject) [{len(ads_rules)}] ---\n"
    new_body += "\n".join(ads_rules) + "\n"
    new_body += "\n# Final Match\nFINAL,DIRECT\n"

    new_content_no_time = header_content.strip() + "\n\n" + new_body
    old_content_no_time = get_content_without_timestamp(old_content_raw)

    # 4. 比對內容 (移除空白與換行後比對)
    if new_content_no_time.strip() == old_content_no_time.strip():
        print("規則內容未變更，跳過更新。")
        # 這裡我們不寫入檔案，這樣檔案修改時間就不會變，Git 就不會偵測到變更
    else:
        # 內容有變，加上時間戳並寫入
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        final_content = header_content.strip() + "\n\n"
        final_content += f"# Updated: {current_time}\n"
        final_content += new_body
        
        with open(conf_file, "w", encoding="utf-8") as f:
            f.write(final_content)
        print(f"規則已有更新，已寫入 {conf_file}")

if __name__ == "__main__":
    main()
