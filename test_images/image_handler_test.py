# test_image_service.py
import unittest
from unittest.mock import patch, MagicMock
import json
import base64
from Service.image_service_handler import lambda_handler
from Service.image_service_handler import ImageServiceHandler


class TestImageService(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.user_id = "test-user-123"
        self.image_id = "test-image-123"
        self.auth_context = {
            'requestContext': {
                'authorizer': {
                    'claims': {
                        'sub': self.user_id
                    }
                }
            }
        }

    @patch('image_service.s3_client')
    @patch('image_service.table')
    def test_upload_image_success(self, mock_table, mock_s3):
        """Test successful image upload"""
        # Prepare test data
        image_data = b"fake-image-data"
        metadata = {
            'title': 'Test Image',
            'description': 'Test Description'
        }

        event = {
            **self.auth_context,
            'body': base64.b64encode(image_data).decode(),
            'isBase64Encoded': True,
            'headers': {
                'content-type': 'image/jpeg',
                'x-image-metadata': json.dumps(metadata)
            }
        }

        mock_s3.put_object.return_value = {}
        mock_table.put_item.return_value = {}

        response = ImageServiceHandler.upload_image(event)

        self.assertEqual(response['status_code'], 200)
        response_body = json.loads(response['body'])
        self.assertIn('imageId', response_body)
        self.assertIn('metadata', response_body)

        mock_s3.put_object.assert_called_once()
        mock_table.put_item.assert_called_once()

    @patch('image_service.table')
    def test_list_images_with_filters(self, mock_table):
        # Prepare test data
        test_images = [
            {
                'imageId': 'image1',
                'title': 'Test Image 1',
                'tags': ['test', 'example']
            }
        ]

        event = {
            **self.auth_context,
            'queryStringParameters': {
                'title': 'Test',
                'tag': 'example'
            }
        }

        mock_table.scan.return_value = {'Items': test_images}

        response = ImageServiceHandler.list_images(event)

        self.assertEqual(response['status_code'], 200)
        response_body = json.loads(response['body'])
        self.assertEqual(len(response_body['images']), 1)
        self.assertEqual(response_body['count'], 1)

    @patch('image_service.s3_client')
    @patch('image_service.table')
    def test_get_image_success(self, mock_table, mock_s3):
        """Test successful image retrieval"""
        test_metadata = {
            'imageId': self.image_id,
            'userId': self.user_id,
            's3Key': 'test/key.jpg'
        }

        event = {
            **self.auth_context,
            'pathParameters': {
                'imageId': self.image_id
            }
        }

        # Configure mocks
        mock_table.get_item.return_value = {'Item': test_metadata}
        mock_s3.generate_presigned_url.return_value = 'https://test-url'

        response = ImageServiceHandler.get_image(event)

        self.assertEqual(response['status_code'], 200)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body['imageId'], self.image_id)
        self.assertIn('downloadUrl', response_body)

    @patch('image_service.s3_client')
    @patch('image_service.table')
    def test_delete_image_success(self, mock_table, mock_s3):
        test_metadata = {
            'imageId': self.image_id,
            'userId': self.user_id,
            's3Key': 'test/key.jpg'
        }

        event = {
            **self.auth_context,
            'pathParameters': {
                'imageId': self.image_id
            }
        }

        # Configure mocks
        mock_table.get_item.return_value = {'Item': test_metadata}
        mock_s3.delete_object.return_value = {}
        mock_table.delete_item.return_value = {}

        # Execute test
        response = ImageServiceHandler.delete_image(event)

        # Verify response
        self.assertEqual(response['status_code'], 200)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body['imageId'], self.image_id)

    def test_invalid_image_type(self):
        event = {
            **self.auth_context,
            'body': base64.b64encode(b"fake-data").decode(),
            'isBase64Encoded': True,
            'headers': {
                'content-type': 'text/plain',
                'x-image-metadata': json.dumps({
                    'title': 'Test',
                    'description': 'Test'
                })
            }
        }

        response = ImageServiceHandler.upload_image(event)
        self.assertEqual(response['status_code'], 400)
        self.assertIn('error', json.loads(response['body']))

    def test_invalid_image_size(self):
        fake_image_length = b"fake" *  10000
        event = {
            **self.auth_context,
            'body': base64.b64encode(fake_image_length).decode(),
            'isBase64Encoded': True,
            'headers': {
                'content-type': 'image/jpeg',
                'x-image-metadata': json.dumps({
                    'title': 'Test',
                    'description': 'Test'
                })
            }
        }

        response = ImageServiceHandler.upload_image(event)
        self.assertEqual(response['status_code'], 400)
        self.assertIn('error', json.loads(response['body']))
