"""Assign or propagate a request correlation id."""

import logging
import re
import uuid
from collections.abc import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger(__name__)

_ID_PATTERN = re.compile(r"^[a-zA-Z0-9-]{8,128}$")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Populate ``request.state.request_id`` and echo it on the response."""

    def __init__(self, app: Callable[..., object], *, header_name: str) -> None:
        super().__init__(app)
        self._header_name = header_name

    async def dispatch(self, request: Request, call_next: Callable[[Request], object]) -> Response:
        raw = request.headers.get(self._header_name)
        if raw and _ID_PATTERN.match(raw):
            request_id = raw
        else:
            request_id = str(uuid.uuid4())
            if raw:
                logger.debug("Ignoring malformed inbound %s: %r", self._header_name, raw)

        request.state.request_id = request_id
        response: Response = await call_next(request)  # type: ignore[assignment]
        response.headers[self._header_name] = request_id
        return response
