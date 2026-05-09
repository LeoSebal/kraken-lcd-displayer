#!/bin/bash

# Path to the service file
SERVICE_FILE="daemon/kraken-lcd.service.template"
SERVICE_TARGET_FILE="/etc/systemd/system/kraken-lcd.service"
UDEV_FILE="daemon/60-nzxt-kraken.rules"
UDEV_TARGET_FILE="/etc/udev/rules.d/60-nzxt-kraken.rules"
ENV_NAME=.venv

CWD=$(realpath .)

# Install virtual environment
if [ ! -d "$ENV_NAME" ]; then
    uv venv "$ENV_NAME"
fi
source $ENV_NAME/bin/activate
uv pip install -r requirements.txt

# Install udev files; backup if necessary
if [ -f "$UDEV_FILE" ]; then
    if [ -f "$UDEV_TARGET_FILE" ] && cmp -s "$UDEV_TARGET_FILE" "$UDEV_TARGET_FILE.bak"; then
        :
    else
        if [ -f "$UDEV_TARGET_FILE" ]; then
            sudo mv "$UDEV_TARGET_FILE" "$UDEV_TARGET_FILE.bak"
            echo "udev rule $UDEV_TARGET_FILE was found: moving to $UDEV_TARGET_FILE.bak"
        fi
        sudo cp "$UDEV_FILE" "$UDEV_TARGET_FILE"
        echo "Successful added udev rule: $UDEV_TARGET_FILE"
    fi # Close the inner if statement
else
    echo "Error: $UDEV_FILE not found."
    exit 1
fi

# Install service file, replacing
if [ -f "$SERVICE_FILE" ]; then
    # Read the template content into a shell variable
    SERVICE_CONTENT=$(<"$SERVICE_FILE")

    # Perform shell variable substitutions
    SERVICE_CONTENT="${SERVICE_CONTENT//\$USER/$USER}"
    SERVICE_CONTENT="${SERVICE_CONTENT//\$CWD/$CWD}"
    SERVICE_CONTENT="${SERVICE_CONTENT//\$ENV_NAME/$ENV_NAME}"
    echo "$SERVICE_CONTENT" | sudo tee "$SERVICE_TARGET_FILE" > /dev/null
    echo "Successfully installed $SERVICE_TARGET_FILE"
else
    echo "Error: $SERVICE_FILE not found."
    exit 1
fi

# Reload daemon
./reload-daemon.sh

exit 0