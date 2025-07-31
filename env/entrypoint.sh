#!/bin/bash

echo "========================================="
echo "  LangChain Development Environment"
echo "========================================="
echo "Python version: $(python --version)"
echo "Conda environment: $CONDA_DEFAULT_ENV"
echo ""
echo "Available packages:"
pip list | grep -E "(langchain|langgraph|openai|jupyter)" || echo "No matching packages found"
echo ""
echo "Code directory: /project/main"
echo "Environment directory: /project/env"
echo ""
echo "========================================="
echo "  Starting Jupyter Lab Server..."
echo "========================================="
echo "Server binding to: 0.0.0.0:8888"
echo "Access URLs:"
echo "  - Local: http://localhost:8888"
echo "  - Network: http://0.0.0.0:8888"
echo "  - Your IP: http://[YOUR_SERVER_IP]:8888"
echo "No token required for development environment"
echo ""

# Jupyter Lab을 백그라운드에서 시작
nohup jupyter lab --config=/project/env/jupyter_config.py > /project/jupyter.log 2>&1 &

# 잠시 대기 후 서버 상태 확인
sleep 3
if pgrep -f "jupyter" > /dev/null; then
    echo "✅ Jupyter Lab started successfully!"
else
    echo "❌ Jupyter Lab failed to start. Check logs:"
    tail -10 /project/jupyter.log
fi

echo "Check logs: tail -f /project/jupyter.log"
echo ""
echo "========================================="
echo "  Ready for development!"
echo "========================================="
echo ""

# 전달받은 명령어 실행
exec "$@"