#!/usr/bin/env bash
# 通用服务器初始化脚本：安装依赖并准备目录，不复制应用文件或 .env 实值。

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/usking}"
DATA_DIR="${DATA_DIR:-/data/usking}"
ENABLE_NGINX="${ENABLE_NGINX:-1}"

if [[ "${EUID}" -ne 0 ]]; then
  echo "请使用 root 或 sudo 运行该脚本。" >&2
  exit 1
fi

log() {
  printf '[deploy/setup] %s\n' "$1"
}

ensure_cmd() {
  command -v "$1" >/dev/null 2>&1
}

install_docker() {
  if ensure_cmd docker; then
    log "Docker 已安装。"
    return
  fi

  log "安装 Docker ..."
  curl -fsSL https://get.docker.com -o /tmp/get-docker.sh
  sh /tmp/get-docker.sh
  systemctl enable docker
  systemctl start docker
}

install_compose() {
  if docker compose version >/dev/null 2>&1; then
    log "docker compose 已可用。"
    return
  fi

  if ensure_cmd apt-get; then
    log "安装 docker compose 插件 ..."
    apt-get update
    apt-get install -y docker-compose-plugin
  fi

  if docker compose version >/dev/null 2>&1; then
    log "docker compose 插件安装完成。"
    return
  fi

  if ensure_cmd docker-compose; then
    log "检测到 docker-compose 独立命令。"
    return
  fi

  log "未检测到 docker compose；请手动安装 docker-compose-plugin 或 docker-compose。"
  exit 1
}

install_nginx() {
  if [[ "${ENABLE_NGINX}" != "1" ]]; then
    log "跳过 Nginx 安装（ENABLE_NGINX=${ENABLE_NGINX}）。"
    return
  fi

  if ensure_cmd nginx; then
    log "Nginx 已安装。"
    return
  fi

  if ensure_cmd apt-get; then
    log "安装 Nginx ..."
    apt-get update
    apt-get install -y nginx
    systemctl enable nginx
    systemctl start nginx
    return
  fi

  log "未检测到 apt-get，无法自动安装 Nginx；请手动安装。"
}

prepare_dirs() {
  log "创建应用目录：${APP_DIR}"
  mkdir -p "${APP_DIR}"
  chmod 755 "${APP_DIR}"

  log "创建数据目录：${DATA_DIR}"
  mkdir -p "${DATA_DIR}/uploads"
  chmod -R 755 "${DATA_DIR}"
}

install_docker
install_compose
install_nginx
prepare_dirs

log "初始化完成。"
log "下一步：同步仓库到 ${APP_DIR}，创建 .env，然后运行 deploy/start.sh。"
