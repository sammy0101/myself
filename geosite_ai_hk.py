import requests
import json
import yaml
import os

# 1. 上游位址
SOURCE_URL = "https://github.com/MetaCubeX/meta-rules-dat/raw/refs/heads/meta/geo/geosite/category-ai-!cn.list"

# 2. 香港直連白名單 (包含這些關鍵字的網域將被剔除，即不走代理)
HK_DIRECT_KEYWORDS = [
    # ========================================================
    # 🌟 Google 服務 (香港已開放直連，但 AI Studio/API 仍需代理)
    # ========================================================
    "gemini.google",
    "bard.google.com",
    "notebooklm.google",
    "labs.google",
    "generativeai.google",
    "jules.google",
    "opal.google",
    "gemini.gstatic.com",
    "antigravity.google",
    "antigravity-unleash.goog",
    "stitch.withgoogle.com",
    "proactivebackend-pa.googleapis.com",

    # ========================================================
    # 🌟 Microsoft / GitHub Copilot (香港可直連)
    # ========================================================
    "githubcopilot.com",
    "copilot-proxy.githubusercontent.com",
    "copilot-workspace.githubnext.com",
    "copilotprodattachments.blob.core.windows.net",
    "copilot-telemetry-service.githubusercontent.com",
    "copilot-telemetry.githubusercontent.com",
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
    "agentclientprotocol.com", "crewai.com", "arena.ai",

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
    # 🌟 工作流、助理與非 AI 誤判網域 (香港直連)
    # ========================================================
    "dify.ai", "coze.com", "jasper.ai",
    "x.ai", "grok.com", "grok.x.com",
    "gateway.ai.cloudflare.com", "pplx-res.cloudinary.com",
    "browser-intake-datadoghq.com", "o33249.ingest.sentry.io",
    "manus.im", "manuscdn.com",
    "envato.com", "envato-static.com", "envatousercontent.com", "themeforest.net",
    "liveperson.net", "lpsnmedia.net", "crixet.com"
]

def smart_write(filename, new_content):
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                old_content = f.read()
            if old_content.strip() == new_content.strip():
                print(f"[{filename}] 內容未變更，跳過寫入。")
                return
        except Exception:
            pass

    with open(filename, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"[{filename}] 已更新。")

def main():
    print(f"正在從 {SOURCE_URL} 下載規則...")
    try:
        response = requests.get(SOURCE_URL, timeout=10)
        response.raise_for_status()
        lines = response.text.splitlines()
    except Exception as e:
        print(f"下載失敗: {e}")
        return

    # 我們需要準備兩個列表
    list_for_singbox = [] # 乾淨的域名 (openai.com)
    list_for_clash = []   # 帶通配符的域名 (+.openai.com)
    
    print("正在處理並過濾規則...")
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        is_direct = False
        for keyword in HK_DIRECT_KEYWORDS:
            # 檢查上游來源是否命中我們的直連白名單
            if keyword in line:
                is_direct = True
                break
        
        # 如果不是直連域名，則保留 (代表需要代理)
        if not is_direct:
            # 1. 取得乾淨的域名 (移除可能存在的修飾符)
            clean_domain = line.replace("'", "").replace("+.", "")
            
            # 2. 構建 Clash / txt 用的通配符域名
            clash_domain = f"+.{clean_domain}"

            if clean_domain and clean_domain not in list_for_singbox:
                list_for_singbox.append(clean_domain)
                list_for_clash.append(clash_domain)

    print(f"過濾後剩餘代理網域數量: {len(list_for_singbox)}")

    # ------------------------------------------------------------
    # 1. 生成 .list (給 Mihomo/OpenClash 用) -> 使用帶 "+." 的列表
    # ------------------------------------------------------------
    list_content = "\n".join(list_for_clash)
    smart_write("geosite_ai_hk_proxy.list", list_content)

    # ------------------------------------------------------------
    # 2. 生成 .yaml (給 Clash Meta 參考用) -> 使用帶 "+." 的列表
    # ------------------------------------------------------------
    mihomo_payload = {"payload": list_for_clash}
    yaml_content = yaml.dump(mihomo_payload, default_flow_style=False)
    smart_write("geosite_ai_hk_proxy.yaml", yaml_content)

    # ------------------------------------------------------------
    # 3. 生成 .json (給 Sing-box 編譯用) -> 使用乾淨列表
    # ------------------------------------------------------------
    srs_payload = {
        "version": 1,
        "rules": [
            {
                "domain_suffix": list_for_singbox
            }
        ]
    }
    json_content = json.dumps(srs_payload, indent=2)
    smart_write("geosite_ai_hk_proxy.json", json_content)

    # ------------------------------------------------------------
    # 4. 生成 .txt (單行，以逗號分隔，無 "+." 前綴)
    # ------------------------------------------------------------
    txt_content = ",".join(list_for_singbox)
    smart_write("geosite_ai_hk_proxy.txt", txt_content)

    # ------------------------------------------------------------
    # 5. 生成 .dae (給 dae/daed 路由規則用，使用多行分組格式)
    # ------------------------------------------------------------
    domains_formatted = ",\n    ".join(list_for_singbox)
    
    dae_content = f"""# DAE / DAED AI HK Proxy Rules
# 說明：請將以下內容貼上至 dae/daed 的 routing {{ ... }} 區塊內。
domain(
    {domains_formatted}
) -> proxy
"""
    smart_write("geosite_ai_hk_proxy.dae", dae_content)

if __name__ == "__main__":
    main()
