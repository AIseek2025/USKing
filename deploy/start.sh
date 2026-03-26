#!/usr/bin/env bash
# 在固定应用目录内启动或重启 USKing，不复制 .env，不生成快照目录。

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/usking}"
COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.prod.yml}"

log() {
  printf '[deploy/start] %s\n' "$1"
}

compose_cmd() {
  if docker compose version >/dev/null 2>&1; then
    docker compose "$@"
    return
  fi

  if command -v docker-compose >/dev/null 2>&1; then
    docker-compose "$@"
    return
  fi

  echo "未检测到 docker compose 或 docker-compose。" >&2
  exit 1
}

if [[ ! -d "${APP_DIR}" ]]; then
  echo "应用目录不存在：${APP_DIR}" >&2
  exit 1
fi

cd "${APP_DIR}"

if [[ ! -f "${COMPOSE_FILE}" ]]; then
  echo "找不到 compose 文件：${APP_DIR}/${COMPOSE_FILE}" >&2
  exit 1
fi

if [[ ! -f ".env" ]]; then
  echo "找不到 ${APP_DIR}/.env，请先按 docs/DEPLOY.md 创建生产环境配置。" >&2
  exit 1
fi

log "停止旧容器（如果存在）..."
compose_cmd -f "${COMPOSE_FILE}" down || true

log "构建并启动服务..."
compose_cmd -f "${COMPOSE_FILE}" up -d --build

log "服务已启动。"
log "宿主机反代端口应对齐 docker-compose.prod.yml 当前映射：127.0.0.1:8002"
log "查看状态：cd ${APP_DIR} && $(if docker compose version >/dev/null 2>&1; then echo 'docker compose'; else echo 'docker-compose'; fi) -f ${COMPOSE_FILE} ps"
