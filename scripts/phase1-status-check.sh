#!/bin/bash
# Phase 1 Implementation Status Check
# Runs every 10 minutes via cron

WORKSPACE=/home/smoke01/.openclaw/workspace-cclow
STATUS_FILE=$WORKSPACE/state/phase1-status.json
LOG_FILE=$WORKSPACE/logs/phase1-status.log

mkdir -p $(dirname $STATUS_FILE) $(dirname $LOG_FILE)

echo "$(date -Iseconds) — Checking Phase 1 status..." >> $LOG_FILE

# Check which modules exist
check_module() {
    local name=$1
    local path=$2
    if [ -f "$path" ]; then
        lines=$(wc -l < "$path")
        echo "\"$name\": {\"status\": \"done\", \"lines\": $lines}"
    else
        echo "\"$name\": {\"status\": \"pending\"}"
    fi
}

# Build status JSON
cat > $STATUS_FILE << EOF
{
  "timestamp": "$(date -Iseconds)",
  "modules": {
    $(check_module "errors" "/tmp/codex-errors/backend/shared/errors.py")
    $(check_module "contracts-mimo" "/tmp/mimo-contracts/backend/shared/contracts/__init__.py")
    $(check_module "contracts-glm" "/tmp/glm-contracts/backend/shared/contracts/__init__.py")
    $(check_module "contracts-claude" "/tmp/claude-contracts/backend/shared/contracts/__init__.py")
    $(check_module "contracts-codex" "/tmp/codex-contracts/backend/shared/contracts/__init__.py")
  }
}
EOF

echo "Status written to $STATUS_FILE" >> $LOG_FILE
