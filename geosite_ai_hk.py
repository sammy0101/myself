import requests
import json
import yaml
import os

# 1. 上游位址
SOURCE_URL = "https://github.com/MetaCubeX/meta-rules-dat/raw/refs/heads/meta/geo/geosite/category-ai-!cn.list"

# 2. 香港直連白名單
HK_DIRECT_KEYWORDS = [
    # ----------------------------------------
    # 1. 開源社群與模型託管 (Open Source & Hosting)
    # ----------------------------------------
    "huggingface.co",   # 全球最大的 AI 模型與數據集社區
    "hf.space",         # Hugging Face Spaces (演示應用)
    "hf.co",            # Hugging Face 短域名
    "chutes.ai",        # AI 基礎設施與部署平台

    # ----------------------------------------
    # 2. AI 搜尋與聚合對話平台 (Search & Chatbots)
    # ----------------------------------------
    "perplexity.ai",    # AI 搜尋引擎 (香港可用，推薦)
    "perplexity.com",
    "poe.com",          # Quora 旗下 AI 聚合平台 (香港可用)
    "poecdn.net",       # Poe 的資源 CDN
    "ciciai.com",       # 字節跳動旗下 Cici AI (海外版豆包)
    "cici.com",
    "ciciaicdn.com",
    "diabrowser.com",   # 專為 AI 設計的瀏覽器
    "dola.com",         # AI 日曆與助理

    # ----------------------------------------
    # 3. 程式開發與 IDE (Coding Assistants)
    # ----------------------------------------
    "cursor.com",       # VS Code Fork 的 AI 編輯器 (香港可用)
    "cursor.sh",
    "cursorapi.com",    # Cursor API 接口
    "cursor-cdn.com",   # Cursor 資源下載
    "trae.ai",          # 字節跳動推出的 AI IDE
    "marscode.com",     # 豆包/MarsCode 編程助手
    "devin.ai",         # Cognition AI (全自動工程師)
    "coderabbit.ai",    # AI Code Review 工具
    "coderabbit.gallery.vsassets.io", # VS Code 插件資源

    # ----------------------------------------
    # 4. 模型 API 與推理加速 (Inference & APIs)
    # ----------------------------------------
    "mistral.ai",       # 法國開源模型強者 (香港可直連)
    "cohere.ai",        # 企業級 NLP 模型
    "cohere.com",
    "groq.com",         # LPU 推理加速芯片 (速度極快)
    "cerebras.ai",      # 晶圓級芯片 AI
    "openrouter.ai",    # 模型 API 聚合商 (香港可直連調用)
    "deepmind.google",  # Google DeepMind 資訊頁 (非 Gemini 聊天)
    "deepmind.com",

    # ----------------------------------------
    # 5. 圖像、媒體與生成式內容 (Media & Generation)
    # ----------------------------------------
    "elevenlabs.io",    # 頂級 AI 語音生成
    "elevenlabs.com",
    "clipdrop.co",      # Stability AI 圖像工具
    "comfy.org",        # ComfyUI 官網
    "comfyregistry.org",# ComfyUI 插件註冊表
    "comfyci.org",      # ComfyUI 持續集成
    "openart.ai",       # AI 繪畫生成與社區

    # ----------------------------------------
    # 6. 應用構建與工作流 (App Builders & Workflow)
    # ----------------------------------------
    "dify.ai",          # 開源 LLM 應用開發平台
    "coze.com",         # 扣子 (Coze) 國際版 (香港可用)
    "jasper.ai",        # 行銷文案 AI

    # ----------------------------------------
    # 7. 社交與馬斯克系列 (Social & xAI)
    # ----------------------------------------
    "x.ai",             # Elon Musk 的 xAI 公司
    "grok.com",         # Grok 模型官網
    "grok.x.com",       # X (Twitter) 內置的 Grok (需會員)
    
    # ----------------------------------------
    # 8. 基礎設施與監控 (Infrastructure & CDN)
    # ----------------------------------------
    "gateway.ai.cloudflare.com",    # Cloudflare AI Gateway
    "pplx-res.cloudinary.com",      # Perplexity 圖片資源
    "browser-intake-datadoghq.com", # 監控日誌
    "o33249.ingest.sentry.io",      # 錯誤追蹤
    
    # ----------------------------------------
    # 9. Azure/OpenAI CDN (特殊情況)
    # ----------------------------------------
    # 註：雖然這些 CDN 域名在香港不被封鎖，但 OpenAI 主服務(openai.com)被鎖。
    # 這些通常是微軟 Azure 託管的資源，部分開發場景可能用到。
    "openaiapi-site.azureedge.net",
    "production-openaicom-storage.azureedge.net",

    # ----------------------------------------
    # ⚠️ 存疑/需注意 (Warning)
    # ----------------------------------------
    # 微軟 Copilot 消費者版在香港並未正式開放，通常會顯示「不支援該地區」。
    # 除非是企業版 (M365) 配置，否則通常需要代理。
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
