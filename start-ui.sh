#!/bin/bash
# Enterprise RAG Chatbot Streamlit UI Startup Script

cd "$(dirname "$0")"

# Activate virtual environment
if [ -d ".venv" ]; then
    . .venv/bin/activate
else
    echo "Error: Virtual environment not found at .venv"
    echo "Please create it first: python3.12 -m venv .venv"
    exit 1
fi

# Install Streamlit if not present
pip show streamlit > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "Installing Streamlit..."
    pip install -q streamlit==1.28.1
fi

echo ""
echo "================================"
echo "🚀 Starting Enterprise RAG UI"
echo "================================"
echo ""
echo "📍 Opening browser at:"
echo "   http://localhost:8501"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

streamlit run ui.py
