class ServiceError(Exception):
    def __init__(self, code: str, message: str, status: int = 503, retry_after: int | None = None):
        super().__init__(message)
        self.code, self.message, self.status, self.retry_after = code, message, status, retry_after
