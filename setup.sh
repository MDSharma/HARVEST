#!/bin/bash

# Setup script for Text2Trait annotation system
# Installs dependencies and prepares the environment

set -e

echo "Setting up Text2Trait annotation system..."
echo ""

# Check Python version
echo "Checking Python version..."
python3 --version || { echo "Error: Python 3 is required"; exit 1; }

# Install Python dependencies
echo ""
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo ""
echo "Creating directories..."
mkdir -p pdfs
mkdir -p logs

# Initialize database
echo ""
echo "Initializing database..."
python3 -c "from t2t_store import init_db; import os; init_db(os.environ.get('T2T_DB', 't2t.db'))"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Setup complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next steps:"
echo "1. Edit .env file to set your admin email (T2T_ADMIN_EMAILS)"
echo "2. Run: ./start_all.sh to start all services"
echo ""
echo "Or start services individually:"
echo "  python3 t2t_training_be.py       # Main backend (port 5001)"
echo "  python3 t2t_admin_be.py          # Admin backend (port 5002)"
echo "  python3 t2t_training_fe.py       # Main frontend (port 8050)"
echo "  python3 t2t_admin_fe.py          # Admin frontend (port 8051)"
echo ""
