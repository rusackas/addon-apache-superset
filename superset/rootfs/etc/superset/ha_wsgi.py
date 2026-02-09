"""
WSGI wrapper for Home Assistant ingress support.

This module wraps the Superset Flask app with middleware that handles
the X-Ingress-Path header set by Home Assistant's ingress proxy.
"""

from superset.app import create_app


class HAIngressMiddleware:
    """Middleware to handle Home Assistant ingress path."""

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        # Get the ingress path from HA's header
        ingress_path = environ.get("HTTP_X_INGRESS_PATH", "")

        if ingress_path:
            # Set SCRIPT_NAME so Flask generates correct URLs
            script_name = ingress_path.rstrip("/")
            environ["SCRIPT_NAME"] = script_name

            # Adjust PATH_INFO if it includes the ingress path
            path_info = environ.get("PATH_INFO", "")
            if path_info.startswith(script_name):
                environ["PATH_INFO"] = path_info[len(script_name):] or "/"

        return self.app(environ, start_response)


# Create the wrapped application
_app = create_app()
application = HAIngressMiddleware(_app)
