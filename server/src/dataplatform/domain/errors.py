"""Domain errors. The API layer maps each one to an RFC 9457 problem response."""


class DomainError(Exception):
    """Base class for expected, client-facing errors."""

    status_code = 400
    title = "Bad request"
    type_suffix = "bad-request"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class InvalidRequestError(DomainError):
    """The request is syntactically valid but its values are not acceptable."""

    status_code = 400
    title = "Invalid request"
    type_suffix = "validation"


class NotFoundError(DomainError):
    """The requested resource does not exist."""

    status_code = 404
    title = "Not found"
    type_suffix = "not-found"


class ConflictError(DomainError):
    """The request conflicts with the current platform state (e.g. a disabled agent)."""

    status_code = 409
    title = "Conflict"
    type_suffix = "conflict"


class QueryError(DomainError):
    """A SQL statement was rejected or failed."""

    status_code = 400
    title = "Query failed"
    type_suffix = "query"


class QueryTimeoutError(QueryError):
    """A SQL statement exceeded the configured timeout."""

    title = "Query timed out"
    type_suffix = "query-timeout"
