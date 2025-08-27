#!/bin/bash

set -eo pipefail

log() {
  echo "$(date -u +'%Y-%m-%d %H:%M:%S UTC') - $1"
}

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

# <-- 變更點 4：簡化名稱邏輯，直接使用傳入的變數
if [ -z "$INPUT_VM_NAME" ]; then
  log "❌ 錯誤: 未提供 INPUT_VM_NAME 環境變數。"
  exit 1
fi
VM_NAME="$INPUT_VM_NAME"
log "將要創建的虛擬機器名稱: $VM_NAME"

MAX_RETRIES=${MAX_RETRIES:-3}
RETRY_DELAY=${RETRY_DELAY:-600}
Jitter_RANGE=${JITTER_RANGE:-60}
log "策略: 共 $MAX_RETRIES 次嘗試，基礎延遲 ${RETRY_DELAY}s，隨機延遲 ${JITTER_RANGE}s。"

# ... 腳本的其餘部分 (重試循環等) 保持不變 ...
