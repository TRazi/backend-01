#!/usr/bin/env python
"""
Setup S3 CORS configuration for kinwise-app bucket
Run: python scripts/setup_s3_cors.py
"""

import boto3
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get AWS credentials and bucket from environment
aws_access_key = os.getenv("AWS_ACCESS_KEY_ID")
aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_region = os.getenv("AWS_REGION", "ap-southeast-2")
bucket_name = os.getenv("AWS_S3_BUCKET_NAME", "kinwise-app")

if not aws_access_key or not aws_secret_key:
    print("❌ Error: AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY not found in .env")
    exit(1)

# Create S3 client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=aws_access_key,
    aws_secret_access_key=aws_secret_key,
    region_name=aws_region,
)

# CORS configuration
cors_config = {
    "CORSRules": [
        {
            "AllowedHeaders": ["*"],
            "AllowedMethods": ["GET", "HEAD"],
            "AllowedOrigins": ["http://127.0.0.1:8000", "http://localhost:8000", "https://*"],
            "ExposeHeaders": ["ETag", "x-amz-version-id"],
            "MaxAgeSeconds": 3000,
        }
    ]
}

try:
    s3_client.put_bucket_cors(Bucket=bucket_name, CORSConfiguration=cors_config)
    print(f"✅ CORS configuration successfully applied to bucket: {bucket_name}")
    print("\nCORS Rules:")
    print(f"  - Allowed Methods: GET, HEAD")
    print(f"  - Allowed Origins: http://127.0.0.1:8000, http://localhost:8000, https://*")
    print(f"  - Allowed Headers: *")
    print(f"  - Max Age: 3000 seconds")
except Exception as e:
    print(f"❌ Error applying CORS configuration: {e}")
    exit(1)
