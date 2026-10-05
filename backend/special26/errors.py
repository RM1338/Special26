"""Special26Error and the error envelope codes (07 §9)."""


class Special26Error(Exception):
    code = "INTERNAL"
    http_status = 500

    def __init__(self, message: str = "", details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class BadRequest(Special26Error):
    code, http_status = "BAD_REQUEST", 400


class NotFound(Special26Error):
    code, http_status = "NOT_FOUND", 404


class ConflictState(Special26Error):
    code, http_status = "CONFLICT_STATE", 409


class Expired(Special26Error):
    code, http_status = "EXPIRED", 410


class PayloadTooLarge(Special26Error):
    code, http_status = "PAYLOAD_TOO_LARGE", 413


class UnsupportedMedia(Special26Error):
    code, http_status = "UNSUPPORTED_MEDIA", 415


class ValidationError(Special26Error):
    code, http_status = "VALIDATION_ERROR", 422


class RateLimited(Special26Error):
    code, http_status = "RATE_LIMITED", 429


class BudgetExhausted(Special26Error):
    code, http_status = "BUDGET_EXHAUSTED", 429


class ReplayMiss(Special26Error):
    code = "REPLAY_MISS"


class UpstreamError(Special26Error):
    code = "UPSTREAM"
