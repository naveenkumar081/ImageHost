import json
import logging
import os
import uuid
from typing import Any

from base64 import b64decode
from common.exception_handler import ImageServiceError
from common import utils
from common import aws_client_adapter
from datetime import datetime

logger = logging.getLogger()
logger.setLevel(logging.INFO)
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'image-storage-bucket')


class ImageServiceHandler:
    def __init__(self):
        pass

    def upload_image(self,
                     event: dict[str, Any],
                     /) -> dict[str, Any]:
        """
        Uploading the image in to the s3 bucket and saving the same data in to the table
        @event: it is dict which contains the details about the lambda handler event
        """
        try:
            if 'body' not in event:
                raise ImageServiceError("No body found in request")

            body = event['body']
            if event.get('isBase64Encoded', False):
                body = b64decode(body)

            content_type = event['headers'].get('content-type', '')
            user_id = event['requestContext']['authorizer']['claims']['sub']
            metadata = utils.process_metadata(event['headers'].get('x-image-metadata', '{}'))

            image_id = str(uuid.uuid4())
            s3_key = f"images/{user_id}/{image_id}.bin"

            utils.validate_image(content_type, len(body))

            aws_client_adapter.put_object_in_to_bucket(BUCKET_NAME,
                                                       s3_key,
                                                       body,
                                                       user_id,
                                                       content_type)

            item = {
                'imageId': image_id,
                'userId': user_id,
                'fileName': f"{image_id}.bin",
                'contentType': content_type,
                's3Key': s3_key,
                'status': 'active',
                'description': metadata['description']
            }

            aws_client_adapter.put_item_in_to_dynamo_table(item)

            return utils.create_response(200, {
                'imageId': image_id,
                'metadata': item
            })

        except ImageServiceError as e:
            logger.error(f"Validation error: {str(e)}")
            return utils.create_response(e.status_code, {}, message=str(e))
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return utils.create_response(500, {}, message="Internal Server Error...")

    def get_image(self,
                  event: dict[str, Any]) -> dict[str, Any]:
        """Get image details and generate download URL"""
        try:
            image_id = event['pathParameters']['imageId']
            user_id = event['requestContext']['authorizer']['claims']['sub']
            key_to_check_in_table = {'imageId': image_id,
                                     'userId': user_id}
            response = aws_client_adapter.get_item_from_table(key_to_check_in_table)

            if 'Item' not in response:
                raise ImageServiceError("Image not found", 404)

            metadata = response['Item']
            s3_key = metadata['s3Key']

            presigned_url = aws_client_adapter.generate_presigned_url_for_object(
                BUCKET_NAME,
                s3_key
            )

            return utils.create_response(200, {
                'imageId': image_id,
                'downloadUrl': presigned_url,
                'metadata': metadata
            })
        except Exception as e:
            logger.error(f"Error retrieving image: {str(e)}")
            return utils.create_response(500,  {}, message='Internal server error')

    def delete_image(self,
                     event: dict[str, Any],
                     /) -> dict[str, Any]:
        """delete the image from the table and the bucket"""
        try:
            image_id = event['pathParameters']['imageId']
            user_id = event['requestContext']['authorizer']['claims']['sub']

            key_to_check_in_table = {'imageId': image_id,
                                     'userId': user_id}

            response = aws_client_adapter.get_item_from_table(
                key_to_check_in_table
            )

            if 'Item' not in response:
                raise ImageServiceError("Image not found", 404)

            s3_key = response['Item']['s3Key']

            aws_client_adapter.delete_object_from_bucket(BUCKET_NAME, s3_key)

            aws_client_adapter.delete_an_item_from_table(
                key_to_check_in_table
            )

            return utils.create_response(200, {
                'message': 'Image deleted successfully',
                'imageId': image_id
            })

        except Exception as e:
            logger.error(f"Error deleting image: {str(e)}")
            return utils.create_response(500,  {}, message='Internal server error')


def lambda_handler(event: dict[str, Any],
                   context: Any,
                   /) -> dict[str, Any]:
    """Main Lambda handler which takes care of the api actions"""
    logger.info(f"Received event: {json.dumps(event)}")

    service = ImageServiceHandler()
    http_method = event['httpMethod']
    resource = event['resource']

    try:
        if http_method == 'POST' and resource == '/images':
            return service.upload_image(event)
        elif http_method == 'DELETE' and resource == '/images':
            return service.delete_image(event)
        elif http_method == 'GET' and resource == '/images/{imageId}':
            return service.delete_image(event)
        else:
            return utils.create_response(405, {}, message="Method not allowed")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return utils.create_response(500, {'error': 'Internal server error'})
