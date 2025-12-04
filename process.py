import requests
import json
import yaml

# 1. 上游地址
SOURCE_URL = "https://github.com/MetaCubeX/meta-rules-dat/raw/refs/heads/meta/geo/geosite/category-ai-!cn.list"

# 2. 你的过滤关键词 (在此列表中的将被剔除)
HK_DIRECT_KEYWORDS = [
    "x.com",             # X (Twitter)
    "x.ai",              # Grok
    "anthropic",         # Claude
    "poe.com",           # Poe
    "poecdn",
    "perplexity",        # Perplexity
    "bing.com",          # Bing
    "bing.net",
    "copilot",
    "huggingface.co"     # HuggingFace
]

def main():
    print(f"Downloading from {SOURCE_URL}...")
    try:
        response = requests.get(SOURCE_URL, timeout=10)
        response.raise_for_status()
        lines = response.text.splitlines()
    except Exception as e:
        print(f"Error downloading: {e}")
        return

    domain_list = []
    
    print("Processing rules...")
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # 过滤逻辑
        is_direct = False
        for keyword in HK_DIRECT_KEYWORDS:
            if keyword in line:
                is_direct = True
                break
        
        if not is_direct:
            # 清理可能的注释或修饰符，保留纯域名
            # MetaCubeX 源通常是纯域名或带 +. 的域名
            clean_domain = line.replace("+,", "").replace("'", "")
            domain_list.append(clean_domain)

    print(f"Total domains after filter: {len(domain_list)}")

    # 1. 生成纯文本 .list 文件 (通用的文本规则)
    with open("geosite_ai_hk_proxy.list", "w", encoding="utf-8") as f:
        f.write("\n".join(domain_list))

    # 2. 生成 Mihomo 源格式 (.yaml) -> 用于编译 .mrs
    # 格式: payload: [domain1, domain2...]
    mihomo_payload = {"payload": domain_list}
    with open("geosite_ai_hk_proxy.yaml", "w", encoding="utf-8") as f:
        yaml.dump(mihomo_payload, f, default_flow_style=False)

    # 3. 生成 Sing-box 源格式 (.json) -> 用于编译 .srs
    # Sing-box 推荐使用 domain_suffix 匹配大部分规则
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

    print("Source files generated: .list, .yaml, .json")

if __name__ == "__main__":
    main()
