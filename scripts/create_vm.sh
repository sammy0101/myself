#!/bin/bash

# 啟用更嚴格的錯誤檢查
set -eo pipefail

# --- 函數定義 ---
log() {
  echo "$(date -u +'%Y-%m-%d %H:%M:%S UTC') - $1"
}

# --- 腳本主體 ---
log "腳本開始執行..."

required_vars=(
  OCI_COMPARTMENT_ID OCI_AVAILABILITY_DOMAIN OCI_IMAGE_OCID OCI_SUBNET_ID
  VM_SHAPE OCPU_COUNT MEMORY_IN_GB
)
for var in "${required_vars[@]}"; do
  if [ -z "${!var}" ]; then
    log "❌ 錯誤: 環境變數 $var 未設置。"
    exit 1
  fi
done

if [[ -n "$INPUT_VM_NAME" ]]; then
  VM_NAME="$INPUT_VM_NAME"
else
  VM_NAME="scheduled-a1-vm-$(date +'%Y%m%d-%H%M')"
fi
log "將要創建的虛擬機器名稱: $VM_NAME"

MAX_RETRIES=${MAX_RETRIES:-5}
RETRY_DELAY=${RETRY_DELAY:-600}
JITTER_RANGE=${JITTER_RANGE:-60}
log "策略: 共 $MAX_RETRIES 次嘗試，基礎延遲 ${RETRY_DELAY}s，隨機延遲 ${JITTER_RANGE}s。"

LAST_ERROR_MESSAGE="已達最大重試次數，但未捕獲到詳細錯誤。"

# --- 重試循環 ---
attempt=1
while [ $attempt -le $MAX_RETRIES ]; do
  log "--- 第 $attempt / $MAX_RETRIES 次嘗試建立 VM ---"

  set +e
  output=$(oci compute instance launch \
    --compartment-id "$OCI_COMPARTMENT_ID" \
    --availability-domain "$OCI_AVAILABILITY_DOMAIN" \
    --display-name "$VM_NAME" \
    --shape "$VM_SHAPE" \
    --shape-config "{\"ocpus\": $OCPU_COUNT, \"memoryInGBs\": $MEMORY_IN_GB}" \
    --image-id "$OCI_IMAGE_OCID" \
    --subnet-id "$OCI_SUBNET_ID" \
    --assign-public-ip true \
    --user-data-file ./cloud-init.txt \
    --output json 2>&1)
  exit_code=$?
  set -e

  if [ $exit_code -eq 0 ] && [ -n "$output" ] && echo "$output" | jq -e '.data.id' > /dev/null; then
    INSTANCE_OCID=$(echo "$output" | jq -r '.data.id')
    log "✅ VM 建立請求成功！實例 OCID: $INSTANCE_OCID"
    echo "success=true" >> "$GITHUB_OUTPUT"
    echo "vm_name=$VM_NAME" >> "$GITHUB_OUTPUT"
    echo "instance_ocid=$INSTANCE_OCID" >> "$GITHUB_OUTPUT"
    echo "attempt_count=$attempt" >> "$GITHUB_OUTPUT"
    echo "success_message=VM instance creation request accepted." >> "$GITHUB_OUTPUT"
    exit 0
  fi

  log "❌ 第 $attempt 次嘗試失敗，退出碼: $exit_code"

  # <-- 變更點：採用更強大的「雙重檢查」錯誤解析邏輯
  # 優先嘗試解析 JSON
  json_body=$(echo "$output" | sed -n '/^{/,$p') # 提取從 { 開始的 JSON 部分
  if [ -n "$json_body" ] && echo "$json_body" | jq . >/dev/null 2>&1; then
    ERROR_CODE=$(echo "$json_body" | jq -r '.code // "UNKNOWN"')
    ERROR_MESSAGE=$(echo "$json_body" | jq -r '.message // "No message in JSON."')
  else
    ERROR_CODE="UNKNOWN_FORMAT"
    ERROR_MESSAGE="$output"
  fi

  # 安全網：無論前面的解析結果如何，都對原始輸出進行關鍵字掃描
  # `grep -q -i` 表示不區分大小寫 (-i) 且靜默模式 (-q)
  if echo "$output" | grep -q -i "Out of host capacity"; then
    log "檢測到關鍵字 'Out of host capacity'，強制分類為容量錯誤。"
    ERROR_CODE="OutOfHostCapacity"
  elif echo "$output" | grep -q -i "InsufficientCapacity"; then
    log "檢測到關鍵字 'InsufficientCapacity'，強制分類為容量錯誤。"
    ERROR_CODE="InsufficientCapacity"
  fi
  
  log "最終錯誤碼: $ERROR_CODE"
  log "錯誤訊息摘要: $(echo "$ERROR_MESSAGE" | head -n 1)"

  LAST_ERROR_MESSAGE=$(echo "$ERROR_MESSAGE" | head -n 1 | sed 's/[{}]//g' | cut -c 1-200)

  case "$ERROR_CODE" in
    "QuotaExceeded" | "LimitExceeded")
      log "檢測到配額或限制錯誤，停止重試。"
      break
      ;;
    "OutOfHostCapacity" | "InsufficientCapacity" | "InternalError") # 將 InternalError 也視為可重試的容量問題
      log "檢測到容量不足或內部錯誤，將在延遲後重試。"
      ;;
    "TooManyRequests")
      log "檢測到請求過多錯誤，將在延遲後重試。"
      ;;
    *)
      log "檢測到未分類的錯誤 ($ERROR_CODE)，將在延遲後重試。"
      ;;
  esac

  if [ $attempt -eq $MAX_RETRIES ]; then
    log "已達最大重試次數，停止執行。"
    break
  fi

  jitter=$(shuf -i 0-$JITTER_RANGE -n 1)
  total_delay=$((RETRY_DELAY + jitter))
  log "等待 $total_delay 秒後進行下一次重試..."
  sleep $total_delay

  ((attempt++))
done

# --- 最終失敗處理 ---
log "❌ VM 建立失敗。"
echo "success=false" >> "$GITHUB_OUTPUT"
echo "attempt_count=$attempt" >> "$GITHUB_OUTPUT"
echo "error_message=$LAST_ERROR_MESSAGE" >> "$GITHUB_OUTPUT"
exit 1
