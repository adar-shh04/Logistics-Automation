output "ec2_public_ip" {
  description = "Public IPv4 address of the EC2 instance"
  value       = aws_instance.app.public_ip
}

output "ec2_public_dns" {
  description = "Public DNS name of the EC2 instance"
  value       = aws_instance.app.public_dns
}

output "ec2_instance_id" {
  description = "Instance ID of the EC2 host (for SSM Session Manager)"
  value       = aws_instance.app.id
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket created for document uploads"
  value       = aws_s3_bucket.uploads.id
}

output "ecr_repository_urls" {
  description = "Repository URLs for the three Docker images in Amazon ECR"
  value = {
    api      = aws_ecr_repository.repos["logistics-api"].repository_url
    worker   = aws_ecr_repository.repos["logistics-worker"].repository_url
    frontend = aws_ecr_repository.repos["logistics-frontend"].repository_url
  }
}

output "github_deploy_role_arn" {
  description = "ARN of the IAM role for GitHub Actions OIDC deployment"
  value       = aws_iam_role.github_deploy.arn
}

output "rds_endpoint" {
  description = "Connection endpoint for managed RDS PostgreSQL (empty if use_rds is false)"
  value       = var.use_rds ? aws_db_instance.postgres[0].endpoint : "n/a (container PostgreSQL in use)"
}

output "ssm_parameters" {
  description = "SSM Parameter Store keys created for secrets"
  value = [
    aws_ssm_parameter.db_password.name,
    aws_ssm_parameter.grafana_password.name,
    aws_ssm_parameter.api_key.name
  ]
}
