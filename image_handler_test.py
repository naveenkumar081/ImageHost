# test_image_service.py
import unittest
from unittest.mock import patch, MagicMock
import json
import base64
from image_service_handler import ImageServiceHandler
from image_service_handler import  AWSActions


class TestImageService(unittest.TestCase):

    @classmethod
    def setUp(self):
        """Set up test fixtures"""
        self.user_id = "test-user-123"
        self.fake_image_encoded = b"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/wcAAgEB/RTmVQAAAABJRU5ErkJggg=="
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
        self.available_image_id = "67df89b4-cbaf-4248-8227-83439e71523a"
        self.available_user_id = "default-user-id"

    def tearDown(self):
        # Ensures all mocks are removed after each test
        patch.stopall()

    @patch('image_service_handler.AWSActions.get_s3_client')
    @patch('image_service_handler.AWSActions.get_dynamodb_table')
    def test_upload_image_success(self, mock_table, mock_s3):
        """Test successful image upload"""
        # Prepare test data
        metadata = {
            'title': 'Test Image',
            'description': 'Test Description'
        }
        json_body = {
            'body': base64.b64encode(self.fake_image_encoded).decode(),
            'isBase64Encoded': True,
            'headers': {
                'content-type': 'image/jpeg',
                'x-image-metadata': json.dumps(metadata)
            }
        }


        event = {
            **self.auth_context,
            "body": json.dumps(json_body),
        }

        mock_s3.put_object.return_value = {}
        mock_table.put_item.return_value = {}

        response = ImageServiceHandler().upload_image(event)

        self.assertEqual(response['statusCode'], 200)
        response_body = json.loads(response['body'])
        self.assertIn('imageId', response_body)
        self.assertIn('metadata', response_body)

        mock_s3.put_object.assert_called_once()
        mock_table.put_item.assert_called_once()

    @patch('image_service_handler.AWSActions.get_dynamodb_table')
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

        response = ImageServiceHandler().list_images(event)

        self.assertEqual(response['statusCode'], 200)

    @patch('image_service_handler.AWSActions.get_s3_client')
    @patch('image_service_handler.AWSActions.get_dynamodb_table')
    def test_get_image_success(self, mock_table, mock_s3):
        """Test successful image retrieval"""
        test_metadata = {
            'imageId': self.available_image_id,
            'userId': self.available_user_id,
            's3Key': 'test/key.jpg'
        }

        event = {
            **self.auth_context,
            'pathParameters': {
                'imageId': self.available_image_id
            }
        }

        # Configure mocks
        mock_table.get_item.return_value = {'Item': test_metadata}
        mock_s3.generate_presigned_url.return_value = 'https://test-url'

        response = ImageServiceHandler().get_image(event)

        self.assertEqual(response['statusCode'], 200)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body['imageId'], self.available_image_id)
        self.assertIn('downloadUrl', response_body)

    @patch('image_service_handler.AWSActions.get_s3_client')
    @patch('image_service_handler.AWSActions.get_dynamodb_table')
    def test_get_image_failure(self, mock_table, mock_s3):
        """Test Failure image retrieval"""
        test_metadata = {
            'imageId': self.available_image_id,
            'userId': self.available_user_id,
            's3Key': 'test/key.jpg'
        }

        event = {
            **self.auth_context,
            'pathParameters': {
                'imageId': self.available_image_id
            }
        }

        # Configure mocks
        mock_table.get_item.return_value = {'Item': test_metadata}
        mock_s3.generate_presigned_url.return_value = 'https://test-url'

        response = ImageServiceHandler().get_image(event)

        self.assertEqual(response['statusCode'], 500)
        response_body = json.loads(response['body'])
        self.assertTrue(any('Image not found' in str(value) for value in response_body.values()))


    @patch('image_service_handler.AWSActions.get_dynamodb_table')
    @patch('image_service_handler.AWSActions.get_s3_client')
    def test_delete_image_success(self, mock_get_dynamodb_table, mock_s3):
        test_metadata = {
            'imageId': self.available_image_id,
            'userId': self.available_user_id,
            's3Key': 'test/key.jpg'
        }
        event = {
            **self.auth_context,
            'pathParameters': {
                'imageId': self.available_image_id
            }
        }
        mock_table = MagicMock()
        # Configure mocks
        mock_get_dynamodb_table.get_item.return_value = {'Item': test_metadata}
        mock_get_dynamodb_table.return_value = mock_table
        mock_s3.delete_object.return_value = {}
        mock_table.delete_item.return_value = {}

        # Execute test
        response = ImageServiceHandler().delete_image(event)

        # Verify response
        self.assertEqual(response['statusCode'], 200)
        response_body = json.loads(response['body'])
        self.assertEqual(response_body['imageId'], self.available_image_id)


    @patch('image_service_handler.AWSActions.get_dynamodb_table')
    @patch('image_service_handler.AWSActions.get_s3_client')
    def test_delete_image_failure(self, mock_get_dynamodb_table, mock_s3):
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
        mock_table = MagicMock()
        # Configure mocks
        mock_get_dynamodb_table.get_item.return_value = {'Item': test_metadata}
        mock_get_dynamodb_table.return_value = mock_table
        mock_s3.delete_object.return_value = {}
        mock_table.delete_item.return_value = {}

        # Execute test
        response = ImageServiceHandler().delete_image(event)

        # Verify response
        self.assertEqual(response['statusCode'], 500)
        response_body = json.loads(response['body'])
        self.assertTrue(any('Image not found' in str(value) for value in response_body.values()))



    def test_invalid_image_type(self):
        json_body = {
            'body': base64.b64encode(self.fake_image_encoded).decode(),
            'isBase64Encoded': True,
            'headers': {
                'content-type': 'text/plain',
                'x-image-metadata': json.dumps({
                    'title': 'Test',
                    'description': 'Test'
                })
            }
        }
        event = {
            **self.auth_context,
            "body": json.dumps(json_body),
        }

        response = ImageServiceHandler().upload_image(event)
        self.assertEqual(response['statusCode'], 400)
        self.assertIn('Unsupported image type', json.loads(response['body']['message']))

    def test_invalid_image_size(self):
        fake_image_length = self.fake_image_encoded * 10000
        json_body = {
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

        event = {
            **self.auth_context,
            "body": json.dumps(json_body),
        }

        response = ImageServiceHandler().upload_image(event)
        self.assertEqual(response['statusCode'], 400)
        self.assertIn('error', json.loads(response['body']))


if __name__ == '__main__':
    # Set buffer=False to see print statements immediately
    unittest.TextTestRunner(verbosity=2, buffer=False).run(unittest.defaultTestLoader.loadTestsFromTestCase(TestImageService))