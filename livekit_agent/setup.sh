#!/bin/bash
# Setup script for LiveKit Voice Agent

echo "Setting up LiveKit Voice Agent..."
echo "=================================="

# Check if we're in the livekit_agent directory
if [ ! -f "requirements.txt" ]; then
    echo "Error: Please run this script from the livekit_agent directory"
    echo "Usage: cd livekit_agent && bash setup.sh"
    exit 1
fi

# Install dependencies
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ Setup complete!"
    echo ""
    echo "Next steps:"
    echo "1. Copy .env.example to .env and configure your credentials"
    echo "2. Run the agent: python agent.py"
    echo ""
    echo "For testing without running:"
    echo "  python test_agent.py"
else
    echo ""
    echo "❌ Installation failed. Please check the error messages above."
    exit 1
fi
