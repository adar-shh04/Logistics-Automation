# -----------------------------------------------------------------------------
# Amazon Linux 2023 EC2 Compute Host
# -----------------------------------------------------------------------------

data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }

  filter {
    name   = "state"
    values = ["available"]
  }
}

resource "aws_instance" "app" {
  ami                  = data.aws_ami.amazon_linux_2023.id
  instance_type        = var.instance_type
  iam_instance_profile = aws_iam_instance_profile.ec2.name

  vpc_security_group_ids = [aws_security_group.ec2.id]

  root_block_device {
    volume_size           = 30 # EasyOCR + PyTorch images need ~10-15GB
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  user_data = <<-EOF
              #!/bin/bash
              set -ex

              # Update system and install Docker & Docker Compose
              dnf update -y
              dnf install -y docker git
              systemctl enable --now docker
              usermod -aG docker ec2-user

              # Install Docker Compose plugin
              DOCKER_CONFIG=/usr/local/lib/docker/cli-plugins
              mkdir -p $DOCKER_CONFIG
              curl -SL https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64 -o $DOCKER_CONFIG/docker-compose
              chmod +x $DOCKER_CONFIG/docker-compose

              # Create app directory
              mkdir -p /opt/logistics
              chown -R ec2-user:ec2-user /opt/logistics

              echo "LogisticsAuto server initialization complete."
              EOF

  tags = {
    Name = "${var.app_name}-host"
  }
}
