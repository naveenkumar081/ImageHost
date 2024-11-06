import json

from typing import  Any
from urllib import parse
from exception_handler import ImageServiceError
from definitions import  ImageRequirements
from definitions import ResponseHeaders

def validate_image(content_type: str,
                   size: int,
                   /) -> None:

    if content_type not in ImageRequirements.allowed_types:
        raise ImageServiceError(f"Unsupported image type: {content_type}")

    if size > ImageRequirements.max_size:
        raise ImageServiceError(f"Image size exceeds maximum allowed size")


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


def create_response(status_code: int,
                    body: dict[str, Any],
                    /,
                    *,
                    message: str = None
                    ) -> dict[str, Any]:

    """Creating the response structure for the apis"""
    return {
        'status_code': status_code,
        'headers': ResponseHeaders.headers,
        'body': json.dumps(body, default=str),
        "message": message or ResponseHeaders.message

    }
