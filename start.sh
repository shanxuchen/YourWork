#!/bin/bash
# ========================================
#   YourWork 启动脚本 (Linux/macOS)
# ========================================

echo ""
echo "========================================"
echo "  YourWork 开发服务器"
echo "========================================"
echo ""
echo "[启动] 正在启动服务..."
echo "[访问] http://localhost:8000"
echo "[文档] http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止服务"
echo "========================================"
echo ""

# 检查 Python 是否已安装
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 Python，请先安装 Python 3.12+"
    exit 1
fi

# 检查依赖是否已安装
python3 -c "import fastapi" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "[提示] 正在安装依赖..."
    pip3 install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[错误] 依赖安装失败"
        exit 1
    fi
fi

# 检查数据库是否存在
if [ ! -f "data/yourwork.db" ]; then
    echo "[提示] 正在初始化数据库..."
    python3 init_db.py
    if [ $? -ne 0 ]; then
        echo "[错误] 数据库初始化失败"
        exit 1
    fi
fi

# 启动服务器
echo ""
echo "[信息] 服务启动中..."
python3 main.py
