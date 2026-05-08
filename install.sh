#!/bin/bash

# Path to the service file
SERVICE_FILE="kraken-lcd.service"
TARGET_FILE="/etc/systemd/system/kraken-lcd.service"

if [ -f "$SERVICE_FILE" ]; then
    # Load the file, replace the $USER placeholder, and write to the system service directory
    sed "s/User=\$USER/User=$USER/" "$SERVICE_FILE" | sudo tee "$TARGET_FILE" > /dev/null
    echo "Successfully installed $TARGET_FILE: User set to $USER"
else
    echo "Error: $SERVICE_FILE not found."
    exit 1
fi

sudo systemctl daemon-reload
sudo systemctl enable kraken-lcd.service
sudo systemctl restart kraken-lcd.service
