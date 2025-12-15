# myself - 個人代理規則倉庫

本倉庫用於自動生成和維護個人使用的網路代理規則，主要針對 **AI 服務** 與 **香港 (HK)** 地區服務的分流需求。
規則文件透過 GitHub Actions 自動更新，支援多種主流代理軟體。

## 📂 規則文件列表

| 文件名稱 | 格式 | 描述 | 推薦客戶端 |
| :--- | :--- | :--- | :--- |
| **[`geosite_ai_hk_proxy.yaml`](./geosite_ai_hk_proxy.yaml)** | YAML | Clash 規則集 (Rule Provider) | Clash Verge, Clash.Meta (Mihomo) |
| **[`geosite_ai_hk_proxy.mrs`](./geosite_ai_hk_proxy.mrs)** | Binary | Mihomo 專用二進制規則 | Mihomo (Clash.Meta) |
| **[`geosite_ai_hk_proxy.srs`](./geosite_ai_hk_proxy.srs)** | Binary | Sing-Box 專用二進制規則 | Sing-Box, Nekobox |
| **[`geosite_ai_hk_proxy.json`](./geosite_ai_hk_proxy.json)** | JSON | Sing-Box 規則源文件 | Sing-Box (Source) |
| **[`geosite_ai_hk_proxy.list`](./geosite_ai_hk_proxy.list)** | List | 純域名列表 | Shadowrocket, Quantumult X |
| **[`ai_ad.conf`](./ai_ad.conf)** | Conf | Shadowrocket 模組/配置 | Shadowrocket |
| **[`CF-IPs.txt`](./CF-IPs.txt)** | Text | Cloudflare IP CIDR 列表 | 通用 |

## 🚀 使用方法

### 1. Clash / Mihomo (Rule Provider)
在您的 Clash 設定檔中加入以下 `rule-providers`：

```yaml
rule-providers:
  AI-Services:
    type: http
    behavior: domain
    format: yaml
    url: "https://raw.githubusercontent.com/sammy0101/myself/main/geosite_ai_hk_proxy.yaml"
    path: ./ruleset/geosite_ai_hk.yaml
    interval: 86400
```

### 2. Sing-Box (Rule Set)
在 Sing-Box 的 `route` 設定中加入：

```json
{
  "type": "remote",
  "tag": "geosite-ai-hk",
  "format": "binary",
  "url": "https://raw.githubusercontent.com/sammy0101/myself/main/geosite_ai_hk_proxy.srs",
  "download_detour": "proxy"
}
```

### 3. Shadowrocket (小火箭)
*   **規則集引用:** 進入 `配置` -> `遠程文件` -> `添加規則集`，輸入 URL：
    ```
    https://raw.githubusercontent.com/sammy0101/myself/main/geosite_ai_hk_proxy.list
    ```
*   **模組/配置:** 如果需要使用 `ai_ad.conf`，可直接導入或複製內容使用。

## 🛠️ 自動化與腳本
本倉庫利用 Python 腳本從上游數據源提取規則，並轉換為不同格式。
*   `geosite_ai_hk.py`: 主要邏輯腳本，整合 AI 與 HK 地區規則。
*   `Shadowrocket_rules.py`: 格式轉換工具。
*   自動化工作流 (GitHub Actions) 會定期執行這些腳本，確保規則即時更新。

## ⚠️ 免責聲明
本項目提供的規則文件僅供個人學習、研究及技術測試使用。請務必遵守所在地區的法律法規。
