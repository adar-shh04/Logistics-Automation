# -----------------------------------------------------------------------------
# SSM Parameter Store (SecureString Secrets)
#
# Note: As per architecture ground rules:
# 1. DB password and Grafana password are generated and written to SSM.
#    Because Terraform state will contain these in plain text, state must stay
#    local on the owner's machine (or private encrypted S3 backend).
# 2. The Gemini API key NEVER enters Terraform. The repository owner populates it:
#    aws ssm put-parameter --name /logistics/gemini_api_key --type SecureString --value "<YOUR_KEY>"
#    Terraform only grants IAM read permissions for /logistics/*.
# -----------------------------------------------------------------------------

resource "random_password" "db_password" {
  length           = 24
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

resource "aws_ssm_parameter" "db_password" {
  name        = "/logistics/db_password"
  description = "PostgreSQL database master password"
  type        = "SecureString"
  value       = random_password.db_password.result
}

resource "random_password" "grafana_password" {
  length  = 16
  special = false
}

resource "aws_ssm_parameter" "grafana_password" {
  name        = "/logistics/grafana_password"
  description = "Grafana dashboard admin password"
  type        = "SecureString"
  value       = random_password.grafana_password.result
}

resource "random_id" "api_key" {
  byte_length = 16 # 32 hex chars
}

resource "aws_ssm_parameter" "api_key" {
  name        = "/logistics/api_key"
  description = "API key required for /upload, /status, /transaction endpoints"
  type        = "SecureString"
  value       = var.api_key != "" ? var.api_key : random_id.api_key.hex
}
