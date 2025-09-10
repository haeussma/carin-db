#!/bin/bash

# Start the backend server
echo "Starting backend server..."
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
