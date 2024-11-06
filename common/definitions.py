class ImageRequirements:
    allowed_types = ['image/jpeg', 'image/png', 'image/gif']
    max_size = 5 * 1024 * 1024


class AWSUtils:
    s3_presigned_url_timeout  = 3600
    ENDPOINT_URL = "http://localhost.localstack.cloud:4566"


class ResponseHeaders:
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
    }
    message = "Action performed Successfully"
