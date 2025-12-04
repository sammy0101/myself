import requests

# 1. 上游地址 (MetaCubeX 的 AI 非 CN 列表)
SOURCE_URL = "https://github.com/MetaCubeX/meta-rules-dat/raw/refs/heads/meta/geo/geosite/category-ai-!cn.list"

# 2. 输出文件名
OUTPUT_FILE = "geosite_ai_hk_proxy.list"

# 3. 香港直连白名单 (在此列表中的域名将被剔除，即走直连，不走代理)
# 注意：这里填写的是关键词或根域名，脚本会检查行内容是否包含这些词
HK_DIRECT_KEYWORDS = [
    "x.com",             # X (Twitter)
    "x.ai",              # Grok 相關
    "anthropic",         # Claude
    "poe.com",           # Poe (香港可直连)
    "poecdn",            # Poe CDN
    "perplexity",        # Perplexity (香港可直连)
    "bing.com",          # Bing / Copilot (香港可直连)
    "bing.net",
    "copilot",           # Microsoft Copilot
    "huggingface.co"     # HuggingFace (通常香港可直连，如下载慢可注释掉此行)
]

def main():
    print(f"Downloading from {SOURCE_URL}...")
    try:
        response = requests.get(SOURCE_URL, timeout=10)
        response.raise_for_status()
        lines = response.text.splitlines()
    except Exception as e:
        print(f"Error downloading file: {e}")
        return

    filtered_lines = []
    removed_count = 0

    print("Processing rules...")
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # 检查该行是否包含“香港直连”的关键词
        # 逻辑：如果该行包含任意一个白名单关键词，则跳过（即剔除）
        is_direct = False
        for keyword in HK_DIRECT_KEYWORDS:
            if keyword in line:
                is_direct = True
                break
        
        if is_direct:
            removed_count += 1
            # print(f"Removed (Direct): {line}") # 调试时可开启
        else:
            filtered_lines.append(line)

    # 写入结果
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(filtered_lines))

    print(f"Done! Original lines: {len(lines)}, Removed: {removed_count}, Remaining: {len(filtered_lines)}")
    print(f"Saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
