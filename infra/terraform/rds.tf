# -----------------------------------------------------------------------------
# Optional Managed AWS RDS PostgreSQL (Enabled via use_rds = true)
# -----------------------------------------------------------------------------

resource "aws_db_instance" "postgres" {
  count                  = var.use_rds ? 1 : 0
  identifier             = "${var.app_name}-db"
  allocated_storage      = 20
  max_allocated_storage  = 50
  storage_type           = "gp3"
  engine                 = "postgres"
  engine_version         = "15"
  instance_class         = var.rds_instance_class
  db_name                = "trade_db"
  username               = "postgres"
  password               = random_password.db_password.result
  vpc_security_group_ids = [aws_security_group.rds[0].id]
  publicly_accessible    = false
  skip_final_snapshot    = true
  deletion_protection    = false

  tags = {
    Name = "${var.app_name}-postgres"
  }
}
