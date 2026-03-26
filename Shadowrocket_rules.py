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
AI_EXCLUSIONS =[
    # ----------------------------------------
    # 1. 開源社群與模型託管
    # ----------------------------------------
    "huggingface.co", "hf.space", "hf.co", "chutes.ai",
    # ----------------------------------------
    # 2. AI 搜尋與聚合對話平台
    # ----------------------------------------
    "perplexity.ai", "perplexity.com", "poe.com", "poecdn.net",
    "ciciai.com", "cici.com", "ciciaicdn.com", "diabrowser.com", "dola.com",
    # ----------------------------------------
    # 3. 程式開發與 IDE
    # ----------------------------------------
    "cursor.com", "cursor.sh", "cursorapi.com", "cursor-cdn.com",
    "trae.ai", "marscode.com", "devin.ai", "coderabbit.ai", "coderabbit.gallery.vsassets.io",
    # ----------------------------------------
    # 4. 模型 API 與推理加速
    # ----------------------------------------
    "mistral.ai", "cohere.ai", "cohere.com", "groq.com", "cerebras.ai",
    "openrouter.ai", "deepmind.google", "deepmind.com",
    # ----------------------------------------
    # 5. 圖像、媒體與生成式內容
    # ----------------------------------------
    "elevenlabs.io", "elevenlabs.com", "clipdrop.co",
    "comfy.org", "comfyregistry.org", "comfyci.org", "openart.ai",
    # ----------------------------------------
    # 6. 應用構建與工作流
    # ----------------------------------------
    "dify.ai", "coze.com", "jasper.ai",
    # ----------------------------------------
    # 7. 社交與馬斯克系列
    # ----------------------------------------
    "x.ai", "grok.com", "grok.x.com",
    # ----------------------------------------
    # 8. 基礎設施與監控
    # ----------------------------------------
    "gateway.ai.cloudflare.com", "pplx-res.cloudinary.com",
    "browser-intake-datadoghq.com", "o33249.ingest.sentry.io",
    # ----------------------------------------
    # 9. Azure/OpenAI CDN
    # ----------------------------------------
    "openaiapi-site.azureedge.net", "production-openaicom-storage.azureedge.net",
    # ----------------------------------------
    # Warning
    # ----------------------------------------
    "copilot.microsoft.com", 

    # ----------------------------------------
    # 🌟 Google Gemini 相關 (香港已開放直連)
    # 註：aistudio 不在此名單，將繼續走代理
    # ----------------------------------------
    "gemini.google",
    "gemini.google.com",
    "bard.google.com",
    "generativelanguage.googleapis.com", 
    "proactivebackend-pa.googleapis.com"
]

def fetch_and_parse(url, policy, exclusions=None):
    rules = []
    if exclusions is None: exclusions =[]
    try:
        print(f"Downloading {url}...")
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        lines = resp.text.splitlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"): continue
            
            # 清理網域：移除 "+." 和單引號 "'"
            domain = line.replace("+.", "").replace("'", "").strip()
            if not domain: continue
            
            # 檢查是否命中直連白名單
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
    header_content = "[General]\nbypass-system = true\n"
    
    # 1. 嘗試保留舊檔案的 Header (如果有的話)
    old_content_raw = ""
    if os.path.exists(conf_file):
        try:
            with open(conf_file, "r", encoding="utf-8") as f:
                old_content_raw = f.read()
                if "[Rule]" in old_content_raw:
                    raw_header = old_content_raw.split("[Rule]")[0]
                    # 清理舊 Header 中的時間戳
                    clean_lines =[line for line in raw_header.splitlines() if not line.strip().startswith("# Updated:")]
                    header_content = "\n".join(clean_lines) + "\n"
        except Exception:
            pass

    # 2. 下載新規則
    ai_rules = fetch_and_parse(urls["AI"]["url"], urls["AI"]["policy"], exclusions=AI_EXCLUSIONS)
    ads_rules = fetch_and_parse(urls["Ads"]["url"], urls["Ads"]["policy"])

    # 3. 組合新內容 (主體)
    new_body = "[Rule]\n"
    new_body += f"# --- Category: AI (Proxy) [{len(ai_rules)}] ---\n"
    new_body += "\n".join(ai_rules) + "\n\n"
    new_body += f"# --- Category: Ads (Reject) [{len(ads_rules)}] ---\n"
    new_body += "\n".join(ads_rules) + "\n"
    new_body += "\n# Final Match\nFINAL,DIRECT\n"

    # 4. 用於比對的內容 (不含時間戳)
    new_content_no_time = header_content.strip() + "\n\n" + new_body
    old_content_no_time = get_content_without_timestamp(old_content_raw)

    # 5. 比對並寫入
    if new_content_no_time.strip() == old_content_no_time.strip():
        print(f"[{conf_file}] 規則內容未變更，跳過更新。")
    else:
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        final_content = header_content.strip() + "\n\n"
        final_content += f"# Updated: {current_time}\n"
        final_content += new_body
        
        with open(conf_file, "w", encoding="utf-8") as f:
            f.write(final_content)
        print(f"[{conf_file}] 規則已有更新，已寫入。")

if __name__ == "__main__":
    main()
