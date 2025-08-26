#!/bin/bash

# 啟用更嚴格的錯誤檢查
set -eo pipefail

# --- 函數定義 ---
log() {
  echo "$(date -u +'%Y-%m-%d %H:%M:%S UTC') - $1"
}

# --- 腳本主體 ---
log "腳本開始執行..."

# 檢查必要的環境變數...
# (此處省略了變數檢查，與您現有版本保持一致即可)
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

MAX_RETRIES=${MAX_RETRIES:-0}
RETRY_DELAY=${RETRY_DELAY:-600}
JITTER_RANGE=${JITTER_RANGE:-60}
log "策略: 共 $MAX_RETRIES 次嘗試，基礎延遲 ${RETRY_DELAY}s，隨機延遲 ${JITTER_RANGE}s。"

# <-- 變更點 1：初始化一個變數來保存最後的錯誤訊息
LAST_ERROR_MESSAGE="已達最大重試次數，但未捕獲到詳細錯誤。"

# --- 重試循環 ---
attempt=1
while [ $attempt -le $MAX_RETRIES ]; do
  log "--- 第 $attempt / $MAX_RETRIES 次嘗試建立 VM ---"

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
  ERROR_CODE=$(echo "$output" | jq -r '.code // "UNKNOWN"')
  ERROR_MESSAGE=$(echo "$output" | jq -r '.message // "無法從 OCI CLI 輸出中解析錯誤訊息。"')
  log "錯誤碼: $ERROR_CODE"
  log "錯誤訊息: $ERROR_MESSAGE"

  # <-- 變更點 2：更新最後的錯誤訊息變數，而不是直接輸出
  LAST_ERROR_MESSAGE=$(echo "$ERROR_MESSAGE" | head -n 1 | sed 's/[{}]//g' | cut -c 1-200)

  case "$ERROR_CODE" in
    "QuotaExceeded" | "LimitExceeded")
      log "檢測到配額或限制錯誤，停止重試。"
      break
      ;;
    "OutOfHostCapacity" | "InsufficientCapacity")
      log "檢測到容量不足錯誤，將在延遲後重試。"
      ;;
    "TooManyRequests")
      log "檢測到請求過多錯誤，將在延遲後重試。"
      ;;
    *)
      log "檢測到未分類的錯誤，將在延遲後重試。"
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
# <-- 變更點 3：在最後統一輸出保存的錯誤訊息，確保永不為空
echo "error_message=$LAST_ERROR_MESSAGE" >> "$GITHUB_OUTPUT"
exit 1
