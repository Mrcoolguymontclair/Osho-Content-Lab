#!/bin/bash
set -e
mkdir -p .streamlit
echo "[browser]
gatherUsageStats = false" > .streamlit/config.toml

echo "🚀 Starting App..."
pkill -f python || true
# Run the scheduler
./venv/bin/python scheduler.py &
# Run Streamlit
./venv/bin/streamlit run main.py --server.port 8501 --server.address 0.0.0.0
