import requests
import json
import yaml
import os

# 1. 上游位址 (MetaCubeX 的非中國大陸 AI 列表)
SOURCE_URL = "https://github.com/MetaCubeX/meta-rules-dat/raw/refs/heads/meta/geo/geosite/category-ai-!cn.list"

# 2. 香港直連白名單 (包含這些關鍵字的網域將被剔除，即不走代理)
HK_DIRECT_KEYWORDS = [
    # --- 1. 開源社群與模型託管 ---
    "huggingface.co", "hf.space", "hf.co", "chutes.ai",
    # --- 2. AI 搜尋與聚合對話平台 ---
    "perplexity.ai", "perplexity.com", "poe.com", "poecdn.net",
    "ciciai.com", "cici.com", "ciciaicdn.com", "diabrowser.com", "dola.com",
    # --- 3. 程式開發與 IDE ---
    "cursor.com", "cursor.sh", "cursorapi.com", "cursor-cdn.com",
    "trae.ai", "marscode.com", "devin.ai", "coderabbit.ai", "coderabbit.gallery.vsassets.io",
    # --- 4. 模型 API 與推理加速 ---
    "mistral.ai", "cohere.ai", "cohere.com", "groq.com", "cerebras.ai",
    "openrouter.ai", "deepmind.google", "deepmind.com",
    # --- 5. 圖像、媒體與生成式內容 ---
    "elevenlabs.io", "elevenlabs.com", "clipdrop.co",
    "comfy.org", "comfyregistry.org", "comfyci.org", "openart.ai",
    # --- 6. 應用構建與工作流 ---
    "dify.ai", "coze.com", "jasper.ai",
    # --- 7. 社交與馬斯克系列 ---
    "x.ai", "grok.com", "grok.x.com",
    # --- 8. 基礎設施與監控 ---
    "gateway.ai.cloudflare.com", "pplx-res.cloudinary.com",
    "browser-intake-datadoghq.com", "o33249.ingest.sentry.io",
    # --- 9. Azure/OpenAI CDN (特殊情況) ---
    "openaiapi-site.azureedge.net", "production-openaicom-storage.azureedge.net",
    # --- Warning ---
    "copilot.microsoft.com", 
]

def smart_write(filename, new_content):
    """智慧寫入：只有內容變更時才寫入，避免觸發 Git 更新"""
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

    domain_list = []
    
    print("正在處理並過濾規則...")
    for line in lines:
        line = line.strip()
        # 跳過空行或註解
        if not line or line.startswith("#"):
            continue

        # 過濾邏輯：檢查是否包含白名單關鍵字
        is_direct = False
        for keyword in HK_DIRECT_KEYWORDS:
            if keyword in line:
                is_direct = True
                break
        
        # 如果不是直連域名，則保留
        if not is_direct:
            # 1. 移除單引號 (有些來源會有 'google.com')
            clean_domain = line.replace("'", "")
            
            # 2. 移除開頭的 "+." (標準 V2Ray 格式)
            # Sing-box 的 domain_suffix 只需要 "openai.com" 就能包含所有子域名
            # 如果保留 "+."，Sing-box 編譯會認為這是一個無效的域名格式
            if clean_domain.startswith("+."):
                clean_domain = clean_domain[2:]
            
            # 3. 確保不重複添加
            if clean_domain and clean_domain not in domain_list:
                domain_list.append(clean_domain)

    print(f"過濾後剩餘網域數量: {len(domain_list)}")

    # ------------------------------------------------------------
    # 1. 生成純文字 .list 檔案
    # ------------------------------------------------------------
    # Mihomo 的 convert-ruleset domain text 模式會將這些視為後綴匹配
    list_content = "\n".join(domain_list)
    smart_write("geosite_ai_hk_proxy.list", list_content)

    # ------------------------------------------------------------
    # 2. 生成 Mihomo (Clash Meta) YAML 格式 (.yaml)
    # ------------------------------------------------------------
    mihomo_payload = {"payload": domain_list}
    yaml_content = yaml.dump(mihomo_payload, default_flow_style=False)
    smart_write("geosite_ai_hk_proxy.yaml", yaml_content)

    # ------------------------------------------------------------
    # 3. 生成 Sing-box JSON 格式 (.json) -> 用於編譯 .srs
    # ------------------------------------------------------------
    # 重要：這裡使用的是 "domain_suffix"
    # 在 Sing-box 中，"domain_suffix": ["openai.com"] 
    # 等同於匹配 openai.com 以及 *.openai.com
    # 這就是為什麼我們必須移除 "+." 的原因
    srs_payload = {
        "version": 1,
        "rules": [
            {
                "domain_suffix": domain_list
            }
        ]
    }
    json_content = json.dumps(srs_payload, indent=2)
    smart_write("geosite_ai_hk_proxy.json", json_content)

if __name__ == "__main__":
    main()
