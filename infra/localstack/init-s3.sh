#!/bin/bash
awslocal s3 mb s3://logistics-uploads || true
echo "LocalStack S3 bucket logistics-uploads created."
