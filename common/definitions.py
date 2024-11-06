from dataclasses import dataclass
from datetime import datetime

@dataclass
class ImageMetadata:
    image_id: str
    user_id: str
    file_name: str
    content_type: str
    size: int
    upload_date: datetime
    s3_key: str
    is_deleted: bool
    description: str
    tags: list[str]

    @classmethod
    def from_dict(cls,
                  data: dict[str, any],
                  /) -> 'ImageMetadata':
        return cls(
            image_id=data['image_id'],
            user_id=data['user_id'],
            file_name=data['file_name'],
            content_type=data['content_type'],
            size=data['size'],
            upload_date=datetime.fromisoformat(data['uploadDate']),
            s3_key=data['s3_key'],
            is_deleted=data['is_deleted'],
            description=data['description'],
            tags=data.get('tags', [])
        )


class ImageRequirements:
    allowed_types = ['image/jpeg', 'image/png', 'image/gif']
    max_size = 5 * 1024 * 1024


class ResponseHeaders:
    headers = {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*'
    }
    message = "Action performed Successfully"
