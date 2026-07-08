#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
import threading
import webbrowser


def get_runserver_url():
    address = next((arg for arg in sys.argv[2:] if not arg.startswith("-")), "127.0.0.1:8000")

    if address.isdigit():
        return f"http://127.0.0.1:{address}/"

    if ":" in address:
        host, port = address.rsplit(":", 1)
        if host in {"", "0.0.0.0", "::"}:
            host = "127.0.0.1"
        return f"http://{host}:{port}/"

    return f"http://{address}/"


def open_browser_for_runserver():
    should_open = (
        "runserver" in sys.argv
        and os.environ.get("DJANGO_AUTO_OPEN_BROWSER", "1") != "0"
        and (os.environ.get("RUN_MAIN") == "true" or "--noreload" in sys.argv)
    )

    if should_open:
        threading.Timer(1.0, lambda: webbrowser.open(get_runserver_url())).start()


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    open_browser_for_runserver()
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
