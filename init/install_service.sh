#!/bin/bash
# YourWork 服务安装脚本
# 用法: sudo bash install_service.sh

set -e

# ===== 配置（按实际情况修改）=====
APP_NAME="yourwork"
APP_DIR="/home/$(whoami)/YourWork"
PYTHON_BIN=$(which python3)
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"

echo "========================================="
echo " YourWork 服务安装"
echo "========================================="
echo " 应用目录: ${APP_DIR}"
echo " Python:   ${PYTHON_BIN}"
echo " 服务文件: ${SERVICE_FILE}"
echo "========================================="

# 检查是否 root
if [ "$EUID" -ne 0 ]; then
  echo "错误: 请使用 sudo 运行此脚本"
  echo "  sudo bash $0"
  exit 1
fi

# 检查目录是否存在
if [ ! -d "${APP_DIR}" ]; then
  echo "错误: 目录 ${APP_DIR} 不存在"
  echo "请先 clone 项目或修改脚本中的 APP_DIR"
  exit 1
fi

# 检查 main.py 是否存在
if [ ! -f "${APP_DIR}/main.py" ]; then
  echo "错误: ${APP_DIR}/main.py 不存在"
  exit 1
fi

# 获取实际运行用户（即使 sudo 也能获取真实用户）
REAL_USER="${SUDO_USER:-$(whoami)}"
echo " 运行用户: ${REAL_USER}"
echo ""

# 生成服务文件（替换模板中的占位符）
echo "生成服务文件..."
sed -e "s|youruser|${REAL_USER}|g" \
    -e "s|/home/youruser/YourWork|${APP_DIR}|g" \
    -e "s|/usr/bin/python3|${PYTHON_BIN}|g" \
    "${APP_DIR}/init/yourwork.service" > "${SERVICE_FILE}"

echo "服务文件已写入: ${SERVICE_FILE}"
echo ""

# 重新加载 systemd
echo "重新加载 systemd..."
systemctl daemon-reload

# 启用开机自启
echo "启用开机自启..."
systemctl enable ${APP_NAME}

# 启动服务
echo "启动服务..."
systemctl start ${APP_NAME}

# 等待并检查状态
sleep 2
echo ""
echo "========================================="
systemctl status ${APP_NAME} --no-pager
echo "========================================="
echo ""
echo "安装完成！常用命令："
echo "  sudo systemctl status ${APP_NAME}     # 查看状态"
echo "  sudo systemctl restart ${APP_NAME}    # 重启服务"
echo "  sudo systemctl stop ${APP_NAME}       # 停止服务"
echo "  sudo journalctl -u ${APP_NAME} -f     # 实时日志"
echo ""
echo "更新代码后："
echo "  cd ${APP_DIR} && git pull && sudo systemctl restart ${APP_NAME}"
