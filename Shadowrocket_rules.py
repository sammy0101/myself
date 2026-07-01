import requests
import datetime
import os
import re

# 設定來源網址 (統一使用最穩定的 raw.githubusercontent 格式)
urls = {
    "Ads": {
        "url": "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/refs/heads/meta/geo/geosite/category-ads-all.list",
        "policy": "Reject"
    },
    "AI": {
        "url": "https://github.com/MetaCubeX/meta-rules-dat/raw/refs/heads/meta/geo/geosite/category-ai-!cn.list",
        "policy": "Proxy"
    },
    "China": {
        "url": "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/refs/heads/meta/geo/geosite/cn.list",
        "policy": "DIRECT"
    }
}

# 🌟 香港直連的 AI 排除名單
AI_EXCLUSIONS =[
    # ========================================================
    # 🌟 Hugging Face 相關 (香港可直連)
    # ========================================================
    "huggingface.co", "hf.space", "hf.co",

    # ========================================================
    # 🌟 Google 服務 (香港已開放直連，但 AI Studio/API 仍需代理)
    # ========================================================
    "gemini.google", "bard.google.com", "notebooklm.google", "labs.google",
    "generativeai.google", "jules.google", "opal.google", "gemini.gstatic.com",
    "antigravity.google", "antigravity-unleash.goog", "stitch.withgoogle.com",
    "proactivebackend-pa.googleapis.com",

    # ========================================================
    # 🌟 Microsoft / GitHub Copilot (香港可直連)
    # ========================================================
    "githubcopilot.com", "copilot-proxy.githubusercontent.com",
    "copilot-workspace.githubnext.com", "copilotprodattachments.blob.core.windows.net",
    "copilot-telemetry-service.githubusercontent.com", "copilot-telemetry.githubusercontent.com",
    "copilot.microsoft.com",

    # ========================================================
    # 🌟 搜尋、聚合 & 代理工具 (香港直連)
    # ========================================================
    "perplexity.ai", "perplexity.com", "ppl-ai-file-upload.s3.amazonaws.com",
    "poe.com", "poecdn.net",
    "ciciai.com", "cici.com", "ciciaicdn.com", "diabrowser.com", "dola.com",
    "diabrowser.engineering", "sider.ai",

    # ========================================================
    # 🌟 開發、編譯 & 本地工具 (香港直連)
    # ========================================================
    "cursor.com", "cursor.sh", "cursorapi.com", "cursor-cdn.com",
    "trae.ai", "marscode.com", "devin.ai", "coderabbit.ai", "coderabbit.gallery.vsassets.io",
    "codeium.com", "codeiumdata.com", "windsurf.build", "windsurf.com",
    "ollama.com", "lmstudio.ai", "anythingllm.com", "langchain.com",
    "agentclientprotocol.com", "crewai.com", "arena.ai", "openclaw.ai", "clawhub.ai",
    "chutes.ai",

    # ========================================================
    # 🌟 API、推理平台與媒體 (香港直連)
    # ========================================================
    "mistral.ai", "cohere.ai", "cohere.com", "groq.com", "cerebras.ai",
    "openrouter.ai", "deepmind.google", "deepmind.com",
    "elevenlabs.io", "elevenlabs.com", "clipdrop.co",
    "comfy.org", "comfyregistry.org", "comfyci.org", "openart.ai",
    "midjourney.com", "mozilla.ai", "h2o.ai", "kiro.dev", "lovart.ai",
    "minimax.io", "openspec.dev", "plannotator.ai", "qoder.com",
    "spicywriter.com", "tapnow.ai", "duck.ai",

    # ========================================================
    # 🌟 工作流、助理與其它 (香港直連)
    # ========================================================
    "dify.ai", "coze.com", "jasper.ai",
    "x.ai", "grok.com", "grok.x.com",
    "gateway.ai.cloudflare.com", "pplx-res.cloudinary.com",
    "browser-intake-datadoghq.com", "o33249.ingest.sentry.io",
    "manus.im", "manuscdn.com",
    "envato.com", "envato-static.com", "envatousercontent.com", "themeforest.net",
    "liveperson.net", "lpsnmedia.net", "crixet.com"
]

def fetch_and_parse(url, policy, exclusions=None):
    rules = []
    if exclusions is None: exclusions = []
    try:
        print(f"Downloading {url}...")
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        lines = resp.text.splitlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"): continue
            
            # 清理網域：移除 "+." 和單引號 "'"
            domain = line.replace("+.", "").replace("'", "").strip()
            if not domain: continue
            
            # 檢查是否命中直連白名單 (只針對傳入名單的規則進行檢查)
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

def smart_write_file(filename, header, body):
    """智慧比對寫入檔案，避免無變更時頻繁觸發 git commit"""
    new_content_no_time = header.strip() + "\n\n" + body.strip()
    
    old_content_raw = ""
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                old_content_raw = f.read()
        except Exception:
            pass
            
    old_content_no_time = get_content_without_timestamp(old_content_raw)
    
    if new_content_no_time.strip() == old_content_no_time.strip():
        print(f"[{filename}] 內容未變更，跳過更新。")
    else:
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        final_content = header.strip() + "\n\n"
        final_content += f"# Updated: {current_time}\n"
        final_content += body.strip() + "\n"
        
        with open(filename, "w", encoding="utf-8") as f:
            f.write(final_content)
        print(f"[{filename}] 規則已有更新，已寫入。")

def main():
    # 1. 下載並解析各項規則
    ai_rules = fetch_and_parse(urls["AI"]["url"], urls["AI"]["policy"], exclusions=AI_EXCLUSIONS)
    ads_rules = fetch_and_parse(urls["Ads"]["url"], urls["Ads"]["policy"], exclusions=[])
    china_rules = fetch_and_parse(urls["China"]["url"], urls["China"]["policy"], exclusions=[])

    # ========================================================
    # 輸出 1: ai_ad.conf (原有的 AI 與去廣告規則 - 香港專用版)
    # ========================================================
    # 🌟 升級：加入適合香港本地網路的高速安全 DoH 伺服器
    ai_ad_header = """[General]
bypass-system = true
dns-server = https://cloudflare-dns.com/dns-query, https://dns.google/dns-query
"""
    ai_ad_body = "[Rule]\n"
    # 🌟 修改：去廣告（Reject）移至最上方，保障效能與隱私
    ai_ad_body += f"# --- Category: Ads (Reject) [{len(ads_rules)}] ---\n"
    ai_ad_body += "\n".join(ads_rules) + "\n\n"
    # AI 代理規則隨後
    ai_ad_body += f"# --- Category: AI (Proxy) [{len(ai_rules)}] ---\n"
    ai_ad_body += "\n".join(ai_rules) + "\n"
    ai_ad_body += "\n# Final Match\nFINAL,DIRECT\n"
    
    smart_write_file("ai_ad.conf", ai_ad_header, ai_ad_body)

    # ========================================================
    # 輸出 2: cn_ad.conf (中國用戶專用：分流 + 去廣告 + DoH 防洩漏)
    # ========================================================
    # 升級為 DoH 伺服器配置以防止 DNS 污染與洩漏，配合 FINAL,PROXY
    cn_ad_header = """[General]
bypass-system = true
dns-server = https://dns.alidns.com/dns-query, https://doh.pub/dns-query
fallback-dns-server = https://dns.google/dns-query, https://cloudflare-dns.com/dns-query
ipv6 = false
prefer-ipv6 = false
dns-direct-system = false
skip-proxy = 127.0.0.1, 192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12, localhost, *.local, elinks.loc
"""
    
    cn_ad_body = "[Rule]\n"
    # 本地內網優先直連
    cn_ad_body += "# --- Private & Local Networks (DIRECT) ---\n"
    cn_ad_body += "DOMAIN-SUFFIX,local,DIRECT\n"
    cn_ad_body += "IP-CIDR,127.0.0.0/8,DIRECT\n"
    cn_ad_body += "IP-CIDR,172.16.0.0/12,DIRECT\n"
    cn_ad_body += "IP-CIDR,192.168.0.0/16,DIRECT\n"
    cn_ad_body += "IP-CIDR,10.0.0.0/8,DIRECT\n\n"
    
    # 廣告攔截 (最優先)
    cn_ad_body += f"# --- Category: Ads (Reject) [{len(ads_rules)}] ---\n"
    cn_ad_body += "\n".join(ads_rules) + "\n\n"
    
    # 國內域名直連
    cn_ad_body += f"# --- China Domains (DIRECT) [{len(china_rules)}] ---\n"
    cn_ad_body += "\n".join(china_rules) + "\n\n"
    
    # 國內 IP 兜底直連，其餘國外流量走 PROXY
    cn_ad_body += "# --- China IPs & Match (Proxy) ---\n"
    cn_ad_body += "GEOIP,CN,DIRECT\n"
    cn_ad_body += "FINAL,PROXY\n"
    
    smart_write_file("cn_ad.conf", cn_ad_header, cn_ad_body)

if __name__ == "__main__":
    main()
