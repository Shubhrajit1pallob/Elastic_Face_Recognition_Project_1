#!/bin/bash

# Define the application folder
APP_DIR="/home/ubuntu/app-tier-app"
USER="ubuntu"

# Create the application directory
echo "Setting permissions for application directory..."
sudo chown -R $USER:$USER $APP_DIR

# Environment variables file creation
echo "Creating environment file..."
sudo tee /etc/app-tier.env > /dev/null <<EOF
RECEIVE_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789012/0000000000-req-queue
SEND_QUEUE_URL=https://sqs.us-east-1.amazonaws.com/123456789012/0000000000-resp-queue
INPUT_BUCKET_NAME=0000000000-in-bucket
OUTPUT_BUCKET_NAME=0000000000-out-bucket
DOWNLOAD_PATH=/tmp/images/
EOF
sudo chmod 644 /etc/app-tier.env

echo "Creating images directory..."
sudo mkdir -p /tmp/images
sudo chown -R $USER:$USER /tmp/images

echo "Adding ~/.local/bin to PATH..."
echo 'export PATH="$HOME/.local/bin:$PATH"' >> /home/ubuntu/.bashrc
export PATH="/home/ubuntu/.local/bin:$PATH"

# Install necessary packages
echo "Updating package lists and installing dependencies..."
export DEBIAN_FRONTEND=noninteractive
sudo -E apt-get update -y
sudo -E apt-get install -y python3
sudo -E apt-get install -y python3-pip git
pip3 install --no-cache-dir -r $APP_DIR/requirements.txt
pip3 install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip3 install --no-cache-dir scikit-learn numpy pandas


# Create systemd service file
SERVICE_FILE="/etc/systemd/system/app-tier.service"

echo "Creating systemd service file at $SERVICE_FILE..."

sudo tee $SERVICE_FILE > /dev/null <<EOF
[Unit]
Description=App Tier Service
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
EnvironmentFile=/etc/app-tier.env
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/ubuntu/.local/bin"
ExecStart=/usr/bin/python3 $APP_DIR/backend.py
Restart=always
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

echo "Reloading systemd and enabling service..."
sudo systemctl daemon-reload
sudo systemctl enable app-tier.service
sudo systemctl start app-tier.service