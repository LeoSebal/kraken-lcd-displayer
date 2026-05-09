#!/bin/bash
# Reload daemon
sudo systemctl daemon-reload
sudo systemctl enable kraken-lcd.service
sudo systemctl restart kraken-lcd.service
