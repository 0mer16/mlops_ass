from flask import Flask, jsonify

APP_NAME = "student-ml-api"
APP_VERSION = "1.0.0"

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
