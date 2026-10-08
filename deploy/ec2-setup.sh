#!/usr/bin/env bash
# One-time setup on a fresh Amazon Linux 2023 EC2 instance:
#   bash ec2-setup.sh
# Installs Docker + Compose, adds 2 GB swap (helps t3.small), prepares /opt/housing.
set -euo pipefail

COMPOSE_VERSION=v5.5.1
APP_DIR=/opt/housing

sudo dnf install -y docker
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"

sudo mkdir -p /usr/local/lib/docker/cli-plugins
sudo curl -fsSL -o /usr/local/lib/docker/cli-plugins/docker-compose \
  "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-$(uname -m)"
sudo chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

if [ ! -f /swapfile ]; then
  sudo fallocate -l 2G /swapfile
  sudo chmod 600 /swapfile
  sudo mkswap /swapfile
  sudo swapon /swapfile
  echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab >/dev/null
fi

sudo mkdir -p "$APP_DIR/data/raw" "$APP_DIR/models"
sudo chown -R "$USER":"$USER" "$APP_DIR"
echo "Done. Log out and back in so the docker group applies, then upload files to $APP_DIR."
