import requests
import json
import yaml
import os

# 1. 上游位址
SOURCE_URL = "https://github.com/MetaCubeX/meta-rules-dat/raw/refs/heads/meta/geo/geosite/category-ai-!cn.list"

# 2. 香港直連白名單
HK_DIRECT_KEYWORDS = [
    # 開源 & 模型
    "huggingface.co", "hf.space", "hf.co", "chutes.ai",
    # 搜尋 & 聚合
    "perplexity.ai", "perplexity.com", "poe.com", "poecdn.net",
    "ciciai.com", "cici.com", "ciciaicdn.com", "diabrowser.com", "dola.com",
    # 開發
    "cursor.com", "cursor.sh", "cursorapi.com", "cursor-cdn.com",
    "trae.ai", "marscode.com", "devin.ai", "coderabbit.ai", "coderabbit.gallery.vsassets.io",
    # API & 推理
    "mistral.ai", "cohere.ai", "cohere.com", "groq.com", "cerebras.ai",
    "openrouter.ai", "deepmind.google", "deepmind.com",
    # 媒體
    "elevenlabs.io", "elevenlabs.com", "clipdrop.co",
    "comfy.org", "comfyregistry.org", "comfyci.org", "openart.ai",
    # 工作流
    "dify.ai", "coze.com", "jasper.ai",
    # 社交
    "x.ai", "grok.com", "grok.x.com",
    # 基礎設施
    "gateway.ai.cloudflare.com", "pplx-res.cloudinary.com",
    "browser-intake-datadoghq.com", "o33249.ingest.sentry.io",
    # Azure/OpenAI CDN
    "openaiapi-site.azureedge.net", "production-openaicom-storage.azureedge.net",
    # Warning
    "copilot.microsoft.com", 
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
            if keyword in line:
                is_direct = True
                break
        
        if not is_direct:
            # 1. 取得乾淨的域名 (移除可能存在的修飾符)
            clean_domain = line.replace("'", "").replace("+.", "")
            
            # 2. 構建 Clash 用的通配符域名
            # OpenClash/Mihomo 識別 "+." 為後綴匹配 (Suffix Match)
            clash_domain = f"+.{clean_domain}"

            if clean_domain and clean_domain not in list_for_singbox:
                list_for_singbox.append(clean_domain)
                list_for_clash.append(clash_domain)

    print(f"過濾後剩餘網域數量: {len(list_for_singbox)}")

    # ------------------------------------------------------------
    # 1. 生成 .list (給 Mihomo/OpenClash 用) -> 使用帶 "+." 的列表
    # ------------------------------------------------------------
    # 這樣 OpenClash 讀取時，才會明確知道這些是後綴匹配，
    # 從而正確分流 ios.chat.openai.com
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
    # Sing-box 的 domain_suffix 本身就隱含了 "+." 的功能，
    # 如果填入 "+.openai.com" 反而會報錯或失效。
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

if __name__ == "__main__":
    main()
