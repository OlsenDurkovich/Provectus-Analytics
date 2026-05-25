"""Dash entry point.

Run:
    python app.py
"""
from provectus_analytics.web.app import create_app, main

app = create_app()
server = app.server  # for gunicorn etc.

if __name__ == "__main__":
    main()
