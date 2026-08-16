#!/bin/bash

# Define the absolute path to your virtual environment
ENV_PATH="$HOME/projects/rpi-csi-pose-sensing/.venv"

# Check if the environment directory exists
if [ -d "$ENV_PATH" ]; then
    echo "Activating the virtual environment..."
    
    # Source the activation script using the absolute path
    source "$ENV_PATH/bin/activate"
    
    echo "Environment activated successfully."
else
    echo "Error: Virtual environment not found at '$ENV_PATH'."
    echo "Please ensure the .venv folder exists in the project root."
fi
