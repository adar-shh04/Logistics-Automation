variable "aws_region" {
  description = "AWS region for all infrastructure resources"
  type        = string
  default     = "ap-south-1" # Mumbai
}

variable "environment" {
  description = "Deployment environment name"
  type        = string
  default     = "prod"
}

variable "app_name" {
  description = "Base application identifier for resource naming"
  type        = string
  default     = "logistics-auto"
}

variable "instance_type" {
  description = "EC2 instance type (t3.large recommended: 2 vCPU, 8 GB RAM for EasyOCR & PyTorch; t3.medium: 4 GB RAM)"
  type        = string
  default     = "t3.large"
}

variable "use_rds" {
  description = "Whether to provision managed AWS RDS PostgreSQL (true) or run PostgreSQL in a container on the EC2 instance (false)"
  type        = bool
  default     = false
}

variable "rds_instance_class" {
  description = "Instance class for RDS PostgreSQL if use_rds is true"
  type        = string
  default     = "db.t4g.micro"
}

variable "github_repo" {
  description = "GitHub repository (owner/repo) permitted to assume the deploy role via OIDC"
  type        = string
  default     = "adar-shh04/Logistics-Automation"
}

variable "allowed_ingress_cidrs" {
  description = "CIDR blocks allowed for inbound HTTP (port 80) and HTTPS (port 443)"
  type        = list(string)
  default     = ["0.0.0.0/0"]
}

variable "api_key" {
  description = "Static API key for authenticating API requests. If empty, a random 32-character key will be generated and saved to SSM."
  type        = string
  default     = ""
  sensitive   = true
}
