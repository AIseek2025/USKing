#!/usr/bin/env bash
# 快速探测 TURN 端口是否可达（需本机安装 openssl / nc）。
# 用法: bash scripts/smoke-turn-connectivity.sh turn.example.com
set -euo pipefail
HOST="${1:-}"
if [[ -z "$HOST" ]]; then
  echo "usage: $0 <turn-hostname>"
  exit 1
fi
echo "== TCP 3478 / 5349 =="
nc -vz "$HOST" 3478 || true
nc -vz "$HOST" 5349 || true
echo "== TLS 5349 (10s timeout) =="
timeout 10 openssl s_client -connect "${HOST}:5349" -servername "$HOST" -brief </dev/null 2>&1 | head -20 || true
