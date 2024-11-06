class ImageServiceError(Exception):
    """Custom exception for image service errors"""
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code
