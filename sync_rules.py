import os
import re
import json
import yaml
import requests
import datetime

# ========================================================
# 1. 來源網址設定 (統一使用穩定 raw 連結)
# ========================================================
URL_AI = "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/refs/heads/meta/geo/geosite/category-ai-!cn.list"
URL_ADS = "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/refs/heads/meta/geo/geosite/category-ads-all.list"
URL_CN = "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/refs/heads/meta/geo/geosite/cn.list"

# ========================================================
# 2. 香港直連 AI 白名單 (全域共用單一維護來源)
# ========================================================
HK_DIRECT_KEYWORDS = [
    # 🌟 Hugging Face 相關 (香港可直連)
    "huggingface.co", "hf.space", "hf.co",

    # 🌟 Google 消費端服務 (香港直連；AI Studio/API 絕不加入此處)
    "gemini.google", "bard.google.com", "notebooklm.google", "notebook.google.com",
    "flow.google", "labs.google", "jules.google", "opal.google",
    "gemini.gstatic.com", "antigravity.google", "antigravity-unleash.goog",
    "stitch.withgoogle.com", "proactivebackend-pa.googleapis.com",

    # 🌟 Microsoft / GitHub Copilot (香港可直連)
    "copilot.com", "copilot-stg.com", "copilot.cloud.microsoft",
    "githubcopilot.com", "copilot-proxy.githubusercontent.com",
    "copilot-workspace.githubnext.com", "copilotprodattachments.blob.core.windows.net",
    "copilot-telemetry-service.githubusercontent.com", "copilot-telemetry.githubusercontent.com",
    "copilot.microsoft.com",

    # 🌟 搜尋、聚合 & 代理工具 (香港直連)
    "pplx.ai", "perplexity.ai", "perplexity.com", "ppl-ai-file-upload.s3.amazonaws.com",
    "poe.com", "poecdn.net",
    "ciciai.com", "cici.com", "ciciaicdn.com", "diabrowser.com", "dola.com",
    "diabrowser.engineering", "sider.ai", "talkai.info",

    # 🌟 開發、編譯 & 本地工具 (香港直連)
    "jetbrains.ai", "grazie.ai", "grazie.aws.intellij.net",
    "cursor.com", "cursor.sh", "cursorapi.com", "cursor-cdn.com",
    "trae.ai", "marscode.com", "devin.ai", "coderabbit.ai", "coderabbit.gallery.vsassets.io",
    "codeium.com", "codeiumdata.com", "windsurf.build", "windsurf.com",
    "ollama.com", "lmstudio.ai", "anythingllm.com", "langchain.com",
    "agentclientprotocol.com", "crewai.com", "arena.ai", "openclaw.ai", "clawhub.ai",
    "chutes.ai",

    # 🌟 API、推理平台與媒體 (香港直連)
    "mistral.ai", "cohere.ai", "cohere.com", "groq.com", "cerebras.ai",
    "openrouter.ai", "deepmind.google", "deepmind.com",
    "elevenlabs.io", "elevenlabs.com", "clipdrop.co",
    "comfy.org", "comfyregistry.org", "comfyci.org", "openart.ai",
    "midjourney.com", "mozilla.ai", "h2o.ai", "kiro.dev", "lovart.ai",
    "minimax.io", "openspec.dev", "plannotator.ai", "qoder.com",
    "spicywriter.com", "tapnow.ai", "duck.ai", "novelai.net", "dreamgen.com",
    "tripo3d.ai", "notegpt.io", "deepwiki.com", "deepwiki.org",

    # 🌟 主流華人 AI / 助理 (香港直連)
    "kimi.ai", "moonshot.ai",

    # 🌟 工作流、助理與其它 (香港直連)
    "dify.ai", "coze.com", "jasper.ai",
    "x.ai", "grok.com", "grok.x.com", "grokipedia.com",
    "gateway.ai.cloudflare.com", "pplx-res.cloudinary.com",
    "browser-intake-datadoghq.com", "o33249.ingest.sentry.io",
    "manus.im", "manuscdn.com",
    "envato.com", "envato-static.com", "envatousercontent.com", "themeforest.net",
    "liveperson.net", "lpsnmedia.net", "crixet.com"
]

# 通用的 TUN 繞過與本地跳過參數 (Shadowrocket 共用)
COMMON_SKIP_PROXY = "192.168.0.0/16, 10.0.0.0/8, 172.16.0.0/12, fe80::/10, fc00::/7, localhost, *.local, *.lan, *.internal, e.crashlytics.com, captive.apple.com, sequoia.apple.com, seed-sequoia.siri.apple.com, *.ls.apple.com"
COMMON_BYPASS_TUN = "10.0.0.0/8,100.64.0.0/10,127.0.0.0/8,169.254.0.0/16,172.16.0.0/12,192.0.2.0/24,192.88.99.0/24,192.168.0.0/16,198.18.0.0/15,198.51.100.0/24,203.0.113.0/24,233.252.0.0/24,224.0.0.0/4,255.255.255.255/32,::1/128,::ffff:0:0/96,::ffff:0:0:0/96,64:ff9b::/96,64:ff9b:1::/48,100::/64,2001::/32,2001:20::/28,2001:db8::/32,2002::/16,3fff::/20,5f00::/16,fc00::/7,fe80::/10,ff00::/8"

# ========================================================
# 3. 輔助函式：檔案比對與安全寫入
# ========================================================
def smart_write(filename, new_content):
    """一般檔案智慧比對：完全相同則不觸發磁碟寫入，避免產生無效 Git Commit"""
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                if f.read().strip() == new_content.strip():
                    print(f"[{filename}] 內容未變更，跳過寫入。")
                    return
        except Exception:
            pass

    with open(filename, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"[{filename}] 已更新。")

def smart_write_conf(filename, header, body):
    """Shadowrocket 配置比對：剔除時間戳後比對，僅在規則變更時更新時間戳並寫入"""
    new_no_time = header.strip() + "\n\n" + body.strip()
    old_raw = ""
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                old_raw = f.read()
        except Exception:
            pass
    old_no_time = re.sub(r'# Updated: .*\n', '', old_raw).strip()

    if new_no_time == old_no_time:
        print(f"[{filename}] 內容未變更，跳過寫入。")
    else:
        current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        final_content = f"{header.strip()}\n\n# Updated: {current_time}\n{body.strip()}\n"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(final_content)
        print(f"[{filename}] 規則已有更新，已寫入。")

def fetch_list(url):
    """下載純文字清單並進行清理"""
    print(f"Downloading {url}...")
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    domains = []
    for line in resp.text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        domain = line.replace("+.", "").replace("'", "").strip()
        if domain and domain not in domains:
            domains.append(domain)
    return domains

# ========================================================
# 4. 主執行流程
# ========================================================
def main():
    # --- A. 下載並過濾 AI 名單 (單次下載，全域共用) ---
    raw_ai_domains = fetch_list(URL_AI)
    ai_domains_clean = []
    ai_domains_clash = []

    for domain in raw_ai_domains:
        is_direct = any(kw.lower() in domain.lower() for kw in HK_DIRECT_KEYWORDS)
        if not is_direct:
            ai_domains_clean.append(domain)
            ai_domains_clash.append(f"+.{domain}")

    print(f"過濾後剩餘代理網域數量: {len(ai_domains_clean)}")

    # --- B. 生成 Sing-box / Mihomo / dae / txt 格式檔案 ---
    # 1. .list (Mihomo/OpenClash 用，帶 +.)
    smart_write("geosite_ai_hk_proxy.list", "\n".join(ai_domains_clash))

    # 2. .yaml (Clash Meta Payload 格式)
    smart_write("geosite_ai_hk_proxy.yaml", yaml.dump({"payload": ai_domains_clash}, default_flow_style=False))

    # 3. .json (Sing-box 編譯 SRS 來源格式)
    srs_payload = {"version": 1, "rules": [{"domain_suffix": ai_domains_clean}]}
    smart_write("geosite_ai_hk_proxy.json", json.dumps(srs_payload, indent=2))

    # 4. .txt (純網域單行逗號格式)
    smart_write("geosite_ai_hk_proxy.txt", ",".join(ai_domains_clean))

    # 5. .dae (dae/daed 外部引用格式，一行一個網域)
    smart_write("geosite_ai_hk_proxy.dae", "\n".join(ai_domains_clean))

    # --- C. 下載廣告與中國大陸網域 (Shadowrocket 專用) ---
    ads_domains = fetch_list(URL_ADS)
    cn_domains = fetch_list(URL_CN)

    ads_rules = [f"DOMAIN-SUFFIX,{d},Reject" for d in ads_domains]
    ai_rules = [f"DOMAIN-SUFFIX,{d},Proxy" for d in ai_domains_clean]
    china_rules = [f"DOMAIN-SUFFIX,{d},DIRECT" for d in cn_domains]

    # --- D. 生成 Shadowrocket 配置檔 ---
    # 輸出 1: ai_ad.conf (香港專用版)
    ai_ad_header = f"""[General]
bypass-system = true
ipv6 = false
prefer-ipv6 = false
dns-direct-system = false
skip-proxy = {COMMON_SKIP_PROXY}
bypass-tun = {COMMON_BYPASS_TUN}
dns-server = https://cloudflare-dns.com/dns-query, https://dns.google/dns-query
"""
    ai_ad_body = (
        "[Rule]\n"
        f"# --- Category: Ads (Reject) [{len(ads_rules)}] ---\n" + "\n".join(ads_rules) + "\n\n"
        f"# --- Category: AI (Proxy) [{len(ai_rules)}] ---\n" + "\n".join(ai_rules) + "\n\n"
        "# Final Match\nFINAL,DIRECT\n"
    )
    smart_write_conf("ai_ad.conf", ai_ad_header, ai_ad_body)

    # 輸出 2: cn_ad.conf (中國專用版)
    cn_ad_header = f"""[General]
bypass-system = true
ipv6 = false
prefer-ipv6 = false
dns-direct-system = false
skip-proxy = {COMMON_SKIP_PROXY}
bypass-tun = {COMMON_BYPASS_TUN}
dns-server = https://dns.alidns.com/dns-query, https://doh.pub/dns-query
fallback-dns-server = https://dns.google/dns-query, https://cloudflare-dns.com/dns-query
"""
    cn_ad_body = (
        "[Rule]\n"
        "# --- Private & Local Networks (DIRECT) ---\n"
        "DOMAIN-SUFFIX,local,DIRECT\n"
        "IP-CIDR,127.0.0.0/8,DIRECT\n"
        "IP-CIDR,172.16.0.0/12,DIRECT\n"
        "IP-CIDR,192.168.0.0/16,DIRECT\n"
        "IP-CIDR,10.0.0.0/8,DIRECT\n\n"
        f"# --- Category: Ads (Reject) [{len(ads_rules)}] ---\n" + "\n".join(ads_rules) + "\n\n"
        f"# --- China Domains (DIRECT) [{len(china_rules)}] ---\n" + "\n".join(china_rules) + "\n\n"
        "# --- China IPs & Match (Proxy) ---\n"
        "GEOIP,CN,DIRECT\n"
        "FINAL,PROXY\n"
    )
    smart_write_conf("cn_ad.conf", cn_ad_header, cn_ad_body)

if __name__ == "__main__":
    main()
