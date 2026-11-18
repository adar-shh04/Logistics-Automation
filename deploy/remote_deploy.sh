#!/usr/bin/env bash
# Runs ON the EC2 instance (as root, via SSM Run Command) to deploy one commit.
#
#   remote_deploy.sh <git-sha> <ecr-registry> <s3-bucket> [aws-region] [db-host]
#
# What it does:
#   1. Checks out deploy/ files for <git-sha> from the public GitHub repo
#      into /opt/logistics (compose file + nginx template).
#   2. Reads secrets from SSM Parameter Store with the instance role and writes
#      /opt/logistics/.env (mode 600). Nothing secret is passed on the command
#      line or printed.
#   3. Logs in to ECR with the instance role, pulls the images tagged <git-sha>
#      and restarts the stack.
#
# db-host defaults to "db" (Postgres container, use_rds=false). For RDS pass the
# rds_endpoint Terraform output (host only, no port).
set -euo pipefail

SHA="${1:?git sha required}"
ECR_REGISTRY="${2:?ecr registry required}"
S3_BUCKET="${3:?s3 bucket required}"
AWS_REGION="${4:-ap-south-1}"
DB_HOST="${5:-db}"
REPO_URL="https://github.com/adar-shh04/Logistics-Automation.git"
APP_DIR=/opt/logistics
SRC_DIR="$APP_DIR/src"

log() { echo "[remote_deploy] $*"; }

param() {
  # $1 = name, $2 = "optional" to allow a missing parameter
  local value
  if value=$(aws ssm get-parameter --region "$AWS_REGION" --name "$1" \
      --with-decryption --query Parameter.Value --output text 2>/dev/null); then
    printf '%s' "$value"
  elif [ "${2:-}" = "optional" ]; then
    printf ''
  else
    log "missing required SSM parameter $1" >&2
    exit 1
  fi
}

mkdir -p "$APP_DIR"
if [ ! -d "$SRC_DIR/.git" ]; then
  log "cloning repository"
  git clone --quiet --filter=blob:none --no-checkout "$REPO_URL" "$SRC_DIR"
fi
git -C "$SRC_DIR" fetch --quiet origin "$SHA"
git -C "$SRC_DIR" checkout --quiet --force "$SHA" -- deploy/
cp "$SRC_DIR/deploy/docker-compose.prod.yml" "$APP_DIR/docker-compose.prod.yml"
cp "$SRC_DIR/deploy/nginx.conf.template" "$APP_DIR/nginx.conf.template"

log "writing $APP_DIR/.env from SSM"
DB_PASSWORD=$(param /logistics/db_password)
APP_API_KEY=$(param /logistics/api_key)
GEMINI_API_KEY=$(param /logistics/gemini_api_key optional)
umask 077
cat > "$APP_DIR/.env" <<ENV
ECR_REGISTRY=$ECR_REGISTRY
IMAGE_TAG=$SHA
S3_BUCKET=$S3_BUCKET
AWS_REGION=$AWS_REGION
DB_USER=postgres
DB_NAME=trade_db
DB_PASSWORD=$DB_PASSWORD
DATABASE_URL_JDBC=jdbc:postgresql://$DB_HOST:5432/trade_db
DATABASE_URL=postgresql://postgres:$DB_PASSWORD@$DB_HOST:5432/trade_db
APP_API_KEY=$APP_API_KEY
GEMINI_API_KEY=$GEMINI_API_KEY
ENV
chmod 600 "$APP_DIR/.env"
[ -z "$GEMINI_API_KEY" ] && log "no /logistics/gemini_api_key in SSM: worker will use regex extraction"

log "logging in to ECR"
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$ECR_REGISTRY" >/dev/null

cd "$APP_DIR"
COMPOSE="docker compose --env-file .env -f docker-compose.prod.yml"
if [ "$DB_HOST" != "db" ]; then
  # RDS in use: do not start the Postgres container.
  SERVICES="redis api worker frontend"
else
  SERVICES=""
fi
log "pulling images for $SHA"
$COMPOSE pull $SERVICES
log "starting stack"
$COMPOSE up -d --remove-orphans $SERVICES
docker image prune -f >/dev/null
log "done"
