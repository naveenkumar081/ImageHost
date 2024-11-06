import os
import boto3
from typing import Any
from common.definitions import AWSUtils

def get_s3_client() -> Any:
    return boto3.client('s3')


def get_dynamodb_table() -> Any:
    dynamodb = boto3.resource('dynamodb')
    return dynamodb.Table(os.environ.get('Table_name', 'Image_Data'))


def put_object_in_to_bucket(bucket_name:str,
                            s3_key: str,
                            body: dict[str, Any],
                            user_id: str,
                            content_type: str,
                            /) -> None:

    s3_client = get_s3_client()
    s3_client.put_object(
        Bucket=bucket_name,
        Key=s3_key,
        Body=body,
        ContentType=content_type,
        Metadata={'userId': user_id}
    )

def delete_object_from_bucket(bucket_name:str,
                              s3_key: str,
                              /) -> None:
    s3_client = get_s3_client()
    s3_client.delete_object(Bucket=bucket_name, Key=s3_key)
    return None

def generate_presigned_url_for_object(bucket_name:str,
                              s3_key: str,
                                      /,
                                      *,
                                      action_name: str = "get_object") -> str:
    s3_client = get_s3_client()

    return  s3_client.generate_presigned_url(
        action_name,
        Params={'Bucket': bucket_name, 'Key': s3_key},
        ExpiresIn=AWSUtils.s3_presigned_url_timeout
    )


def put_item_in_to_dynamo_table(item: dict[str, Any],
                                /) -> None:
    table_obj = get_dynamodb_table()
    table_obj.put_item(Item=item)
    return None


def get_item_from_table(key_to_look: dict[str, Any],
                        /) -> dict[str, Any]:
    table_obj = get_dynamodb_table()
    data_to_retrive = table_obj.get_item(Key=key_to_look)
    return data_to_retrive

def delete_an_item_from_table(item: dict[str, Any],
                                /) -> None:
    table_obj = get_dynamodb_table()
    table_obj.delete_item(Item=item)
    return None
