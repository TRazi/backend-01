import environ

env = environ.Env()
env.read_env()  # Read .env file

AWS_S3_BUCKET_NAME = "kinwise-app"


# AWS Configuration
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
AWS_REGION = env("AWS_REGION", default="ap-southeast-2")  
AWS_S3_BUCKET_NAME = env("AWS_S3_BUCKET_NAME", default="")

# AWS Textract Settings
AWS_TEXTRACT_ENABLED = env.bool("AWS_TEXTRACT_ENABLED", default=False)
AWS_TEXTRACT_TIMEOUT = env.int("AWS_TEXTRACT_TIMEOUT", default=30)  # seconds
AWS_TEXTRACT_MAX_FILE_SIZE = env.int(
    "AWS_TEXTRACT_MAX_FILE_SIZE", default=10485760
)  # 10MB

# Receipt Storage Settings
RECEIPT_STORAGE_ENABLED = env.bool("RECEIPT_STORAGE_ENABLED", default=True)
RECEIPT_RETENTION_DAYS = env.int(
    "RECEIPT_RETENTION_DAYS", default=365
)  # 12 months as per spec
RECEIPT_MAX_SIZE_MB = env.int("RECEIPT_MAX_SIZE_MB", default=10)
RECEIPT_ALLOWED_FORMATS = ["jpg", "jpeg", "png", "pdf"]


#Storage settings
AWS_S3_CUSTOM_DOMAIN = f"{AWS_S3_BUCKET_NAME}.s3.amazonaws.com"
AWS_S3_FILE_OVERWRITE = False

