from pathlib import Path

from flask import Flask, jsonify

APP_NAME = "student-ml-api"
VERSION_FILE = Path(__file__).parent / "VERSION"


def read_version():
    # the VERSION file is the one place the app version is kept,
    # so a release only needs that file bumped
    try:
        return VERSION_FILE.read_text().strip()
    except FileNotFoundError:
        return "unknown"


APP_VERSION = read_version()

app = Flask(__name__)


@app.get("/health")
def health():
    return jsonify(
        status="healthy",
        application=APP_NAME,
        version=APP_VERSION,
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
