import datetime


class NextoryBackendError(Exception):
    def __init__(self, type: str, title: str, status: int, detail: str, isntance: str):
        self.type = type
        self.title = title
        self.status = status
        self.detail = detail
        self.instance = isntance
        super().__init__(f"{title} ({status}): {detail}")

class NextoryNetowrkError(Exception):
    """Exception raised for Nextory network errors."""
    def __init__(self, status: int, error: str, path: str, timestamp: datetime.datetime):
        self.status = status
        self.error = error
        self.path = path
        self.timestamp = timestamp
        super().__init__(f"{status} {error} {path}")

class NextoryApiError(Exception):
    """Exception raised for Nextory API errors."""

    def __init__(self, code: int, key: str, message: str, description: str):
        self.code = code
        self.key = key
        self.message = message
        self.description = description
        super().__init__(f"{key} ({code}): {description}")

class ExpiredLoginTokenError(NextoryApiError): # 2001
    pass

class ExpiredProfileTokenError(NextoryApiError): # 2002
    pass

class MaxProfileSessionsError(NextoryApiError): # 2003
    pass

class InvalidAuthTokenError(NextoryApiError): # 1001
    pass

class MissingHeaderError(NextoryApiError): # 1005
    def __init__(self, code: int, key: str, message: str, description: str):
        super().__init__(code, key, message, description)
        import re
        match = re.search(r'\[(.*?)\]|missing\s+(X-[\w-]+)', description)
        if match:
            headers_str = match.group(1) or match.group(2)
            self.missing_headers = [
                h.strip().replace('-', '').lower() for h in headers_str.split(",")
            ]
        else:
            self.missing_headers = []


class MissingParameterError(NextoryApiError): # 1006
    pass



class ProfileNotFoundError(NextoryApiError): # 3010
    pass

class InvalidDataError(NextoryApiError):
    pass

class LibraryApiError(NextoryApiError): # 5000-5999
    pass

class UserApiError(NextoryApiError): # 3000-3499
    pass

class UnauthorizedError(NextoryApiError): # 1001
    pass

class UserNotAuthenticatedError(NextoryApiError): # 1002
    pass


ERROR_CODE_MAP: dict[int, type[NextoryApiError]] = {
    1001: InvalidAuthTokenError,
    1002: UserNotAuthenticatedError,
    1005: MissingHeaderError,
    1006: MissingParameterError,
    1007: InvalidDataError,
    2001: ExpiredLoginTokenError,
    2002: ExpiredProfileTokenError,
    2003: MaxProfileSessionsError,
    3010: ProfileNotFoundError,
    7111: UnauthorizedError,
}

