class AppException(Exception):
    status_code = 400
    default_message = "A custom exception occurred."

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class CustomException(AppException):
    default_message = "A custom exception occurred."


class BadRequestException(AppException):
    default_message = "Bad request."


class NotFoundException(AppException):
    status_code = 404
    default_message = "Resource not found."


class ForbiddenException(AppException):
    status_code = 403
    default_message = "Forbidden."


class UnauthorizedException(AppException):
    status_code = 401
    default_message = "Unauthorized."


class UnprocessableEntityException(AppException):
    status_code = 422
    default_message = "Unprocessable entity."


class DuplicateValueException(AppException):
    status_code = 409
    default_message = "Duplicate value."


class RateLimitException(AppException):
    status_code = 429
    default_message = "Rate limit exceeded."
