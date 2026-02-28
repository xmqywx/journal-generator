#!/bin/bash

# v3量化系统 - Web UI 快速启动脚本

echo "=================================="
echo "v3量化系统 - Web UI启动"
echo "=================================="
echo ""

# 检查是否在正确的目录
if [ ! -f "web_app.py" ]; then
    echo "❌ 错误：请在 quant_v3/live 目录下运行此脚本"
    exit 1
fi

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "🔧 首次运行，正在创建虚拟环境..."
    python3 -m venv venv

    echo "📦 安装依赖..."
    source venv/bin/activate
    pip install -r requirements.txt --quiet

    echo "✅ 虚拟环境创建完成"
    echo ""
fi

# 激活虚拟环境
echo "🚀 启动Web服务器..."
source venv/bin/activate

# 启动Flask
python web_app.py
