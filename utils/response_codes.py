"""
The script shoud contain response and error schemas for the application
and any other schemas that may be needed in the application.
"""

from http import HTTPStatus


class ResponseCodes:
    SUCCESS = str(HTTPStatus.OK)
    FAILURE = str(HTTPStatus.BAD_REQUEST)
    NOT_FOUND = str(HTTPStatus.NOT_FOUND)
    UNAUTHORIZED = str(HTTPStatus.UNAUTHORIZED)
    FORBIDDEN = str(HTTPStatus.FORBIDDEN)
    INTERNAL_SERVER_ERROR = str(HTTPStatus.INTERNAL_SERVER_ERROR)
    BAD_REQUEST = str(HTTPStatus.BAD_REQUEST)
    CREATED = str(HTTPStatus.CREATED)
    NO_CONTENT = str(HTTPStatus.NO_CONTENT)
    NOT_MODIFIED = str(HTTPStatus.NOT_MODIFIED)
    ACCEPTED = str(HTTPStatus.ACCEPTED)
