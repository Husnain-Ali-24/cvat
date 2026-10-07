# Copyright (C) CVAT.ai Corporation
#
# SPDX-License-Identifier: MIT

"""
ASGI config for CVAT project.
"""

import os
from django.core.asgi import get_asgi_application
import cvat.utils.remote_debugger as debug

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cvat.settings.development")

django_http_application = get_asgi_application()


async def application(scope, receive, send):
    """
    ASGI 3.0 dispatcher routing HTTP to Django and WebSocket to cvat.apps.test.websocket.
    """
    if scope["type"] == "websocket" and scope.get("path", "").startswith("/api/test/analytics/ws"):
        from cvat.apps.test.websocket import websocket_application
        await websocket_application(scope, receive, send)
    else:
        await django_http_application(scope, receive, send)
