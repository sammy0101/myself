import requests
import json
import yaml

# 1. 上游位址 (MetaCubeX 的非中國大陸 AI 列表)
SOURCE_URL = "https://github.com/MetaCubeX/meta-rules-dat/raw/refs/heads/meta/geo/geosite/category-ai-!cn.list"

# 2. 香港直連白名單 (包含這些關鍵字的網域將被剔除，即不走代理)
HK_DIRECT_KEYWORDS = [
    "x.com",             # X (Twitter)
    "x.ai",              # Grok 相關
    "anthropic",         # Claude
    "poe.com",           # Poe (香港可直連)
    "poecdn",            # Poe CDN
    "perplexity",        # Perplexity (香港可直連)
    "bing.com",          # Bing / Copilot (香港可直連)
    "bing.net",
    "copilot",           # Microsoft Copilot
    "huggingface.co"     # HuggingFace
]

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
            # 清理可能的修飾符，保留純網域 (MetaCubeX 源通常包含 +, 或 ' )
            clean_domain = line.replace("+,", "").replace("'", "")
            domain_list.append(clean_domain)

    print(f"過濾後剩餘網域數量: {len(domain_list)}")

    # 1. 生成純文字 .list 檔案 (通用格式)
    with open("geosite_ai_hk_proxy.list", "w", encoding="utf-8") as f:
        f.write("\n".join(domain_list))

    # 2. 生成 Mihomo (Clash Meta) 來源格式 (.yaml) -> 用於編譯 .mrs
    mihomo_payload = {"payload": domain_list}
    with open("geosite_ai_hk_proxy.yaml", "w", encoding="utf-8") as f:
        yaml.dump(mihomo_payload, f, default_flow_style=False)

    # 3. 生成 Sing-box 來源格式 (.json) -> 用於編譯 .srs
    srs_payload = {
        "version": 1,
        "rules": [
            {
                "domain_suffix": domain_list
            }
        ]
    }
    with open("geosite_ai_hk_proxy.json", "w", encoding="utf-8") as f:
        json.dump(srs_payload, f, indent=2)

    print("已生成來源檔案: .list, .yaml, .json")

if __name__ == "__main__":
    main()
