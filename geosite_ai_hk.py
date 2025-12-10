import requests
import json
import yaml
import os

# 1. 上游位址 (MetaCubeX 的非中國大陸 AI 列表)
SOURCE_URL = "https://github.com/MetaCubeX/meta-rules-dat/raw/refs/heads/meta/geo/geosite/category-ai-!cn.list"

# 2. 香港直連白名單 (包含這些關鍵字的網域將被剔除，即不走代理)
HK_DIRECT_KEYWORDS = [
    "x.com",             # X (Twitter)
    "x.ai",              # Grok 相關
    "grok.com",          # Grok
    "anthropic",         # Claude
    "poe.com",           # Poe (香港可直連)
    "poecdn",            # Poe CDN
    "perplexity",        # Perplexity (香港可直連)
    "bing.com",          # Bing / Copilot (香港可直連)
    "bing.net",
    "copilot",           # Microsoft Copilot
    "huggingface.co"     # HuggingFace
]

def smart_write(filename, new_content):
    """
    智慧寫入功能：
    先讀取舊檔案，如果內容完全一致，則不進行寫入操作。
    這能避免 Git 偵測到檔案修改，從而節省後續編譯資源。
    """
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                old_content = f.read()
            
            # 比對內容 (移除前後空白以免因換行符號造成誤判)
            if old_content.strip() == new_content.strip():
                print(f"[{filename}] 內容未變更，跳過寫入。")
                return
        except Exception:
            # 如果讀取舊檔失敗，就直接寫入新檔
            pass

    # 內容有變或檔案不存在，執行寫入
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
            # 清理可能的修飾符，保留純網域 (MetaCubeX 源通常包含 +. 或 ' )
            # 這裡保留了你原本正確的寫法 "+."
            clean_domain = line.replace("+.", "").replace("'", "")
            domain_list.append(clean_domain)

    print(f"過濾後剩餘網域數量: {len(domain_list)}")

    # 1. 生成純文字 .list 檔案 (通用格式)
    list_content = "\n".join(domain_list)
    smart_write("geosite_ai_hk_proxy.list", list_content)

    # 2. 生成 Mihomo (Clash Meta) 來源格式 (.yaml) -> 用於編譯 .mrs
    mihomo_payload = {"payload": domain_list}
    # 將 yaml 轉為字串
    yaml_content = yaml.dump(mihomo_payload, default_flow_style=False)
    smart_write("geosite_ai_hk_proxy.yaml", yaml_content)

    # 3. 生成 Sing-box 來源格式 (.json) -> 用於編譯 .srs
    srs_payload = {
        "version": 1,
        "rules": [
            {
                "domain_suffix": domain_list
            }
        ]
    }
    # 將 json 轉為字串
    json_content = json.dumps(srs_payload, indent=2)
    smart_write("geosite_ai_hk_proxy.json", json_content)

if __name__ == "__main__":
    main()
