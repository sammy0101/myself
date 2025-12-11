# myself - 個人代理規則倉庫

這個倉庫用於存儲和自動維護個人使用的網路代理規則，支援多種常見的代理軟體，如 Clash、Sing-Box 和 Shadowrocket。

規則主要包含針對特定服務（如 AI 相關服務）的分流設定，並透過 GitHub Actions 進行自動化更新。

## 📂 文件說明

本倉庫包含以下類型的規則文件，適用於不同的客戶端：

| 文件名稱 | 描述 | 適用軟體/格式 |
| :--- | :--- | :--- |
| **[`Clash_Rules.YAML`](./Clash_Rules.YAML)** | Clash 格式的規則配置 |
| **[`Sing-Box_Rules.JSON`](./Sing-Box_Rules.JSON)** | Sing-Box 格式的規則配置 |
| **[`geosite_ai_hk_proxy.list`](./geosite_ai_hk_proxy.list)** | 純域名列表 (Domain List) |
| **[`geosite_ai_hk_proxy.mrs`](./geosite_ai_hk_proxy.mrs)** | Binary 格式規則 (Mihomo) |
| **[`geosite_ai_hk_proxy.srs`](./geosite_ai_hk_proxy.srs)** | Binary 格式規則 (Sing-Box) |
| **[`geosite_ai_hk_proxy.yaml`](./geosite_ai_hk_proxy.yaml)** | YAML 格式規則集 |
| **[`ai_ad.conf`](./ai_ad.conf)** | AI 去廣告Shadowrocket配置 |
| **[`CF-CIDR.txt`](./CF-CIDR.txt)** | Cloudflare IP CIDR 範圍列表 |

## 🚀 使用方法

### 引用規則連結
建議使用 CDN 加速連結引用規則，以確保更新穩定性：

*   **Clash Rule Provider 範例:**
    ```yaml
    rule-providers:
      AI-Services:
        type: http
        behavior: domain
        url: "https://raw.githubusercontent.com/sammy0101/myself/main/geosite_ai_hk_proxy.yaml"
        path: ./ruleset/ai_services.yaml
        interval: 86400
    ```

*   **Sing-Box Rule Set 範例:**
    ```json
    {
      "type": "remote",
      "tag": "geosite-ai",
      "format": "binary",
      "url": "https://raw.githubusercontent.com/sammy0101/myself/main/geosite_ai_hk_proxy.srs",
      "download_detour": "proxy"
    }
    ```

*   **Shadowrocket:**
    直接在配置中添加 Rule Set URL：
    `https://raw.githubusercontent.com/sammy0101/myself/main/geosite_ai_hk_proxy.list`

### 腳本與自動化
本倉庫包含 Python 腳本（如 `scripts/` 目錄及根目錄下的 `.py` 文件），用於從上游數據源提取、轉換並生成上述規則文件。GitHub Actions 會定期執行這些腳本以保持規則為最新狀態。

*   `geosite_ai_hk.py`: 生成 AI 相關的 GeoSite 規則。
*   `Shadowrocket_rules.py`: 轉換規則為 Shadowrocket 兼容格式。

## ⚠️ 免責聲明
本倉庫提供的規則僅供個人學習與研究使用。請遵守您所在地區的法律法規及網路安全規範。

---
*Last Updated: Automatically updated via GitHub Actions.*
