"""Error types the app raises on purpose.

Each one carries an HTTP status, a short machine-readable `type`, a message
written for a lawyer (not a developer), and optional `details`. A single handler
in main.py turns any of these into the JSON error shape.

Example:
    raise TargetNotFound('Couldn\'t find "Delaware" in this document.', {"find": "Delaware"})

    ...becomes this HTTP response (status 422):
    {
      "error": "Couldn't find \\"Delaware\\" in this document.",
      "code": 422,
      "type": "target_not_found",
      "details": {"find": "Delaware"}
    }
"""


class AppError(Exception):
    """Base class. Each subclass below only changes `status` and `type`."""

    status = 500
    type = "server_error"

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class InvalidRequest(AppError):
    status = 400
    type = "invalid_request"


class NotFound(AppError):
    status = 404
    type = "not_found"


class VersionConflict(AppError):
    status = 409
    type = "version_conflict"


class TooLarge(AppError):
    status = 413
    type = "too_large"


class UnsupportedFileType(AppError):
    status = 415
    type = "unsupported_file_type"


class TargetNotFound(AppError):
    status = 422
    type = "target_not_found"


class AmbiguousTarget(AppError):
    status = 422
    type = "ambiguous_match"


class OccurrenceOutOfRange(AppError):
    status = 422
    type = "occurrence_out_of_range"


class AIServiceError(AppError):
    """The AI provider failed, timed out, or declined the request."""

    status = 502
    type = "ai_unavailable"


class AINotConfigured(AppError):
    status = 503
    type = "ai_not_configured"
