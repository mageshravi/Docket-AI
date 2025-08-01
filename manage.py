#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""

import os
import sys

from django.conf import settings


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "docket_ai.settings")

    if settings.DEBUG:
        if os.getenv("RUN_MAIN") or os.getenv("WERKZEUG_RUN_MAIN"):
            import debugpy

            debugpy.listen(("0.0.0.0", 3000))
            # debugpy.wait_for_client()
            print("Debugpy attached!")

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
