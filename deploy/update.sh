#!/bin/bash
set -e
echo "======================================"
echo "🚀 USKing 一键部署脚本"
echo "======================================"
cd /opt/usking
sudo docker compose -f docker-compose.prod.yml down
sudo git fetch origin
sudo git reset --hard origin/main
sudo sed -i "s/templates\.TemplateResponse(\"\([^\"]*\)\", {\"request\": request})/templates.TemplateResponse(request, \"\1\")/g" server/main.py
sudo rm -rf app server templates static views capture composer stream
if grep -q \"8000:8000\" docker-compose.prod.yml; then sudo sed -i \"s/\"8000:8000\"/\"8002:8000\"/g\" docker-compose.prod.yml; fi
sudo docker compose -f docker-compose.prod.yml up -d --build
sleep 5
sudo docker ps | grep usking-web
echo "✅ 部署完成！访问：https://usking.vip/"
