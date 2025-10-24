#!/bin/bash

# Start all Text2Trait services
# Usage: ./start_all.sh

set -e

echo "Starting Text2Trait Services..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Create PDF storage directory
mkdir -p pdfs

# Start main backend
echo "Starting main backend (port $T2T_BACKEND_PORT)..."
python t2t_training_be.py &
MAIN_BE_PID=$!

# Wait a bit for main backend to start
sleep 2

# Start admin backend
echo "Starting admin backend (port $T2T_ADMIN_PORT)..."
python t2t_admin_be.py &
ADMIN_BE_PID=$!

# Wait a bit for admin backend to start
sleep 2

# Start main frontend
echo "Starting main frontend (port $T2T_FRONTEND_PORT)..."
python t2t_training_fe.py &
MAIN_FE_PID=$!

# Wait a bit for main frontend to start
sleep 2

# Start admin frontend
echo "Starting admin frontend (port $T2T_ADMIN_FRONTEND_PORT)..."
python t2t_admin_fe.py &
ADMIN_FE_PID=$!

echo ""
echo "All services started!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Main Annotation Interface: http://localhost:$T2T_FRONTEND_PORT"
echo "Admin Panel:              http://localhost:$T2T_ADMIN_FRONTEND_PORT"
echo ""
echo "Main Backend API:         http://localhost:$T2T_BACKEND_PORT"
echo "Admin Backend API:        http://localhost:$T2T_ADMIN_PORT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Process IDs:"
echo "  Main Backend:    $MAIN_BE_PID"
echo "  Admin Backend:   $ADMIN_BE_PID"
echo "  Main Frontend:   $MAIN_FE_PID"
echo "  Admin Frontend:  $ADMIN_FE_PID"
echo ""
echo "Press Ctrl+C to stop all services"

# Wait for Ctrl+C
trap "echo 'Stopping all services...'; kill $MAIN_BE_PID $ADMIN_BE_PID $MAIN_FE_PID $ADMIN_FE_PID 2>/dev/null; exit 0" INT TERM

# Wait for all processes
wait
