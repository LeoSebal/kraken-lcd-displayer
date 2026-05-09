#!/bin/bash

SERVICE_FILE="/etc/systemd/system/kraken-lcd.service"
UDEV_FILE="/etc/udev/rules.d/60-nzxt-kraken.rules"
ENV_NAME=.venv

sudo rm "$SERVICE_FILE"
sudo rm "$UDEV_FILE"
sudo rm -rf "$ENV_NAME"

sudo systemctl daemon-reload

echo "Successfully uninstalled"
exit 0