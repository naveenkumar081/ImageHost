import json
import logging
import os
import uuid
import sys

from typing import Any
import mimetypes

from base64 import b64decode

import boto3

possible_top_dir = os.path.normpath(os.path.join(os.path.abspath(sys.argv[0]),
                                                 os.pardir,
                                                 os.pardir))

if os.path.exists(os.path.join(possible_top_dir, 'ImageHost', '__init__.py')):
    sys.path.insert(0, possible_top_dir)


class AWSActions:

    @staticmethod
    def get_s3_client() -> Any:
        return boto3.client('s3', endpoint_url=AWSUtils.ENDPOINT_URL)

    @staticmethod
    def get_dynamodb_table() -> Any:
        dynamodb = boto3.resource('dynamodb', endpoint_url=AWSUtils.ENDPOINT_URL)
        return dynamodb.Table(os.environ.get('Table_name', 'ImageMetaData'))

    @staticmethod
    def put_object_in_to_bucket(bucket_name: str,
                                s3_key: str,
                                body: dict[str, Any],
                                user_id: str,
                                content_type: str,
                                /) -> None:
        s3_client = AWSActions.get_s3_client()
        s3_client.put_object(
            Bucket=bucket_name,
            Key=s3_key,
            Body=body,
            ContentType=content_type,
            Metadata={'userId': user_id}
        )

    @staticmethod
    def delete_object_from_bucket(bucket_name: str,
                                  s3_key: str,
                                  /) -> None:
        s3_client = AWSActions.get_s3_client()
        s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
        return None

    @staticmethod
    def generate_presigned_url_for_object(bucket_name: str,
                                          s3_key: str,
                                          /,
                                          *,
                                          action_name: str = "get_object") -> str:
        s3_client = AWSActions.get_s3_client()

        return s3_client.generate_presigned_url(
            action_name,
            Params={'Bucket': bucket_name, 'Key': s3_key},
            ExpiresIn=AWSUtils.s3_presigned_url_timeout
        )

    @staticmethod
    def put_item_in_to_dynamo_table(item: dict[str, Any],
                                    /) -> None:
        table_obj = AWSActions.get_dynamodb_table()
        table_obj.put_item(Item=item)
        return None

    @staticmethod
    def get_item_from_table(key_to_look: dict[str, Any],
                            /) -> dict[str, Any]:
        table_obj = AWSActions.get_dynamodb_table()
        data_to_retrive = table_obj.get_item(Key=key_to_look)
        return data_to_retrive

    @staticmethod
    def delete_an_item_from_table(item: dict[str, Any],
                                  /) -> None:
        table_obj = AWSActions.get_dynamodb_table()
        table_obj.delete_item(Key=item)
        return None

    @staticmethod
    def scan_items_from_table(filter_expressions: str,
                              values: dict[str, Any],
                              /) -> dict[str, Any]:
        table_obj = AWSActions.get_dynamodb_table()
        data_to_retrive = table_obj.scan(FilterExpression=filter_expressions,
                                         ExpressionAttributeValues=values)
        return data_to_retrive


class ImageRequirements:
    allowed_types = ['image/jpeg', 'image/png', 'image/gif']
    max_size = 5 * 1024 * 1024


class AWSUtils:
    s3_presigned_url_timeout = 3600
    ENDPOINT_URL = "http://localhost.localstack.cloud:4566"


class ResponseHeaders:
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
    }
    message = "Action performed Successfully"


class ImageServiceError(Exception):
    """Custom exception for image service errors"""

    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class Utils:

    @staticmethod
    def validate_image(content_type: str,
                       size: int,
                       /) -> None:

        if content_type not in ImageRequirements.allowed_types:
            raise ImageServiceError(f"Unsupported image type: {content_type}")

        if size > ImageRequirements.max_size:
            raise ImageServiceError(f"Image size exceeds maximum allowed size")

    @staticmethod
    def process_metadata(metadata: str,
                         /) -> dict[str, Any]:
        """Process and validate metadata"""
        try:
            metadata = json.loads(metadata)
            if 'description' not in metadata:
                raise ImageServiceError(f"Missing required metadata key: 'description'")

            return metadata
        except json.JSONDecodeError:
            raise ImageServiceError("Invalid metadata format")

    @staticmethod
    def create_response(status_code: int,
                        body: dict[str, Any],
                        /,
                        *,
                        base_64_encoded: bool = False
                        ) -> dict[str, Any]:

        """Creating the response structure for the apis"""
        return {
            'statusCode': status_code,
            'headers': ResponseHeaders.headers,
            'body': json.dumps(body, default=str),
            "isBase64Encoded": base_64_encoded

        }


logger = logging.getLogger()
logger.setLevel(logging.INFO)
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'imagehost')


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

            body = json.loads(body)

            content_type = body.get('headers', {}).get('content-type', '')
            user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub',
                                                                                                 'default-user-id')
            metadata = Utils.process_metadata(body.get('headers', {}).get('x-image-metadata', '{}'))
            image_id = str(uuid.uuid4())
            file_extension = mimetypes.guess_extension(content_type) or '.bin'
            s3_key = f"images/{user_id}/{image_id}{file_extension}"
            Utils.validate_image(content_type, len(body))

            AWSActions.put_object_in_to_bucket(BUCKET_NAME,
                                               s3_key,
                                               body.get('body'),
                                               user_id,
                                               content_type)

            item = {
                'imageId': image_id,
                'userId': user_id,
                'fileName': f"{image_id}{file_extension}",
                'contentType': content_type,
                's3Key': s3_key,
                'status': 'active',
                'description': metadata['description']
            }

            AWSActions.put_item_in_to_dynamo_table(item)

            return Utils.create_response(200, {
                'imageId': image_id,
                'metadata': item
            })

        except ImageServiceError as e:
            logger.error(f"Validation error: {str(e)}")
            return Utils.create_response(e.status_code, {"message": str(e)})
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return Utils.create_response(500, {"message": f"Internal Server Error::{str(e)}"})

    def fetch_s3_key_from_event_dict(self,
                                     event: dict[str, Any],
                                     /):
        image_id = event['pathParameters']['imageId']
        user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub', 'default-user-id')
        key_to_check_in_table = {'imageId': image_id,
                                 'userId': user_id}

        response = AWSActions.get_item_from_table(
            key_to_check_in_table
        )

        if 'Item' not in response:
            raise ImageServiceError("Image not found", 404)

        s3_key = response['Item']['s3Key']
        metadata = response['Item']

        return key_to_check_in_table, metadata, s3_key

    def get_image(self,
                  event: dict[str, Any]) -> dict[str, Any]:
        """Get image details and generate download URL"""
        try:
            key_to_check_in_table, metadata, s3_key = self.fetch_s3_key_from_event_dict(event)
            image_id = event['pathParameters']['imageId']
            presigned_url = AWSActions.generate_presigned_url_for_object(
                BUCKET_NAME,
                s3_key
            )

            return Utils.create_response(200, {
                'imageId': image_id,
                'downloadUrl': presigned_url,
                'metadata': metadata
            })
        except Exception as e:
            logger.error(f"Error retrieving image: {str(e)}")
            return Utils.create_response(500, {"message": f'Internal server error::{str(e)}'})

    def list_images(self,
                    event: dict[str, Any],
                    /) -> dict[str, Any]:
        """Listing the images """
        try:
            user_id = event.get('requestContext', {}).get('authorizer', {}).get('claims', {}).get('sub',
                                                                                                  'default-user-id')

            query_params = event.get('queryStringParameters', {}) or {}
            filter_expressions = ['userId = :userId']
            expression_values = {':userId': user_id}
            if 'title' in query_params:
                filter_expressions.append('contains(title, :title)')
                expression_values[':title'] = query_params['title']

            if 'tag' in query_params:
                filter_expressions.append('contains(tags, :tag)')
                expression_values[':tag'] = query_params['tag']
            response = AWSActions.scan_items_from_table(' AND '.join(filter_expressions),
                                                        expression_values)

            return Utils.create_response(200, {
                'images': response['Items'],
                'count': len(response['Items'])
            })


        except Exception as e:
            logger.error(f"Error listing images: {str(e)}")
            return Utils.create_response(500, {
                "message": f"Internal server error::{str(e)}"
            })

    def delete_image(self,
                     event: dict[str, Any],
                     /) -> dict[str, Any]:
        """delete the image from the table and the bucket"""
        try:
            key_to_check_in_table, metadata, s3_key = self.fetch_s3_key_from_event_dict(event)
            image_id = event['pathParameters']['imageId']
            AWSActions.delete_object_from_bucket(BUCKET_NAME, s3_key)
            AWSActions.delete_an_item_from_table(
                key_to_check_in_table
            )

            return Utils.create_response(200, {
                'message': 'Image deleted successfully',
                'imageId': image_id
            })

        except Exception as e:
            logger.error(f"Error deleting image: {str(e)}")
            return Utils.create_response(500, {"message": f"Internal server error::{str(e)}"})


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
        elif http_method == 'DELETE' and resource == '/images/{imageId}':
            return service.delete_image(event)
        elif http_method == 'GET' and resource == '/images':
            return service.list_images(event)
        elif http_method == 'GET' and resource == '/images/{imageId}':
            return service.get_image(event)
        else:
            return Utils.create_response(405, {"message": "Method Not Allowed"})
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return Utils.create_response(500, {'error': f'Internal server error::{str(e)}'})
