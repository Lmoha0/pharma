"""
main.py
Launches Biopharma Tracker as a native desktop window using pywebview.
The UI is plain HTML/CSS/JS (web/index.html); all data logic stays in
Python (database.py, api.py) so nothing runs on a remote server.

Run with: python main.py
"""

import webview
import database as db
from api import Api


def main():
    db.init_db()
    api = Api()
    webview.create_window(
        "Biopharma Tracker",
        "web/index.html",
        js_api=api,
        width=1300,
        height=820,
        min_size=(1000, 640),
        background_color="#eef1f8",
    )
    webview.start()


if __name__ == "__main__":
    main()
