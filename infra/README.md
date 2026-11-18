# Infrastructure Deployment Guide (AWS & Terraform)

This directory contains the Terraform Infrastructure-as-Code definitions for deploying the Logistics Automation platform to **AWS Mumbai (`ap-south-1`)**.

---

## 1. Prerequisites & Account Setup

### Step 1.1: AWS Account & Budget Alert (Do this FIRST)
1. Sign in to your [AWS Console](https://console.aws.amazon.com/).
2. Navigate to **AWS Budgets** (`Billing & Cost Management` → `Budgets`).
3. Click **Create budget**:
   - Template: **Zero spend budget** or **Monthly cost budget**.
   - Amount: **\$5.00 – \$10.00 USD**.
   - Notification email: Enter your primary email address.
   - Thresholds: 85% forecasted, 100% actual.
4. Review AWS Free Tier eligibility:
   - AWS Free Tier includes 750 hours of `t2.micro` / `t3.micro` for 12 months, but EasyOCR and PyTorch require at least 4–8 GB RAM (`t3.medium` or `t3.large`).
   - Check current EC2 on-demand and EBS prices before provisioning.

### Step 1.2: Configure AWS Credentials Locally
Ensure you have the AWS CLI installed and configured on your machine:
```bash
aws configure
# Or using AWS IAM Identity Center:
aws configure sso
```
Ensure your IAM user/role has permissions for S3, ECR, IAM, EC2, RDS, VPC, and SSM Parameter Store.

### Step 1.3: Store Gemini API Key in SSM
The Gemini API key **never** enters Terraform code or git. Run this command manually to inject it securely into AWS SSM Parameter Store:
```bash
aws ssm put-parameter \
  --name "/logistics/gemini_api_key" \
  --description "Google Gemini API key for invoice NLP extraction" \
  --type "SecureString" \
  --value "<YOUR_ACTUAL_GEMINI_API_KEY>" \
  --region "ap-south-1"
```

---

## 2. Infrastructure Architecture & Sizing

| Component | AWS Resource | Description & Cost Trade-off |
| :--- | :--- | :--- |
| **Object Storage** | `aws_s3_bucket.uploads` | Encrypted (SSE-S3), private, 30-day auto-expiration lifecycle. Billed per GB stored (~$0.023/GB/mo). |
| **Container Registry**| `aws_ecr_repository` | Repositories for `logistics-api`, `logistics-worker`, `logistics-frontend` with 10-image lifecycle. |
| **IAM Security** | `aws_iam_role.ec2` | Least-privilege instance role: S3 uploads bucket only, ECR pull, SSM core, SSM parameters read. No long-lived keys. |
| **CI/CD Role** | `aws_iam_role.github_deploy` | GitHub OIDC federated role scoped strictly to `repo:adar-shh04/Logistics-Automation:ref:refs/heads/main`. |
| **Compute** | `aws_instance.app` | Default `t3.large` (2 vCPU, 8 GB RAM, ~$0.0832/hr in Mumbai) for EasyOCR + PyTorch. `t3.medium` (4 GB, ~$0.0416/hr) is supported via variable. |
| **Database** | Docker vs RDS | Variable `use_rds=false` runs Postgres in a Docker container ($0 extra). `use_rds=true` provisions `db.t4g.micro` (~$0.018/hr / ~$13/mo). |
| **Cache & Queue** | Docker Redis | Redis 7 runs inside Docker on the EC2 host with named volume persistence. |
| **Networking** | `aws_security_group.ec2` | Inbound HTTP 80 & HTTPS 443 only. **No inbound SSH (port 22)**; shell access is through AWS SSM Session Manager. |

---

## 3. Provisioning Steps (Repository Owner)

Navigate to the terraform directory:
```bash
cd infra/terraform
```

### Step 3.1: Initialize & Review Plan
```bash
# Initialize providers and local state
terraform init

# Generate execution plan
terraform plan -out=tfplan
```
Review the proposed resources. Verify that:
- S3 bucket has public access blocked.
- Security group does NOT expose port 22.
- The region is `ap-south-1`.

### Step 3.2: Apply Infrastructure
```bash
terraform apply tfplan
```
Once complete, note the outputs:
- `ec2_public_ip` / `ec2_public_dns`: Host address.
- `s3_bucket_name`: Created S3 bucket.
- `ecr_repository_urls`: Target URLs for pushing Docker images.
- `github_deploy_role_arn`: Role ARN to add to GitHub repository variables.
- `ssm_parameters`: Parameter names created for secrets.

### Step 3.3: Configure GitHub Actions OIDC
1. In your GitHub repository, go to **Settings** → **Secrets and variables** → **Actions** → **Variables**.
2. Add a new repository variable:
   - Name: `AWS_DEPLOY_ROLE_ARN`
   - Value: `<output.github_deploy_role_arn>`
3. In `.github/workflows/deploy.yml`, change `if: false` to `if: true` (or trigger manually via `workflow_dispatch`) to build and push images to ECR.

---

## 4. Teardown & Cost Management

To destroy all cloud resources and prevent ongoing charges:
```bash
cd infra/terraform
terraform destroy -auto-approve
```

> [!WARNING]
> While active, the following AWS resources incur costs even when idle:
> - **EC2 instance running hours** (`t3.large` ~$2.00/day).
> - **EBS gp3 volumes** (30 GB root volume ~$2.40/month).
> - **Public IPv4 address** (AWS charges ~$0.005/hr / ~$3.60/month per in-use public IPv4 address).
> - **RDS PostgreSQL** (if `use_rds=true`, ~$13.00/month).
>
> Always run `terraform destroy` when you are done demonstrating or testing.
