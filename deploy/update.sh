#!/usr/bin/env bash
# Run on the EC2 instance in /opt/housing to pull the latest image and (re)start the app:
#   bash update.sh
# Needs deploy.env (APP_IMAGE, SITE_ADDRESS, AWS_REGION) and an instance role with ECR read access.
set -euo pipefail
cd "$(dirname "$0")"

set -a; . ./deploy.env; set +a
registry="${APP_IMAGE%%/*}"

# The container runs as UID 10001; it writes the map cache and chat history under data/.
sudo chown -R 10001:10001 data
sudo chmod 640 .env && sudo chown "$USER":10001 .env

aws ecr get-login-password --region "$AWS_REGION" | docker login --username AWS --password-stdin "$registry"
docker compose --env-file deploy.env -f compose.aws.yaml pull
docker compose --env-file deploy.env -f compose.aws.yaml up -d --remove-orphans
docker image prune -f >/dev/null
docker compose --env-file deploy.env -f compose.aws.yaml ps
