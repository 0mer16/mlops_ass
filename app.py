from pathlib import Path

from flask import Flask, jsonify, request

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

# the model has its own version, separate from the app version. in a real
# setup they change for different reasons (new code vs retrained model),
# so /health reports both
MODEL_VERSION = "model-1"

app = Flask(__name__)


def predict(value):
    # placeholder "model", it just doubles the input.
    # the assignment is about the pipeline, not the model
    return value * 2


@app.get("/health")
def health():
    return jsonify(
        status="healthy",
        application=APP_NAME,
        application_version=APP_VERSION,
        model_version=MODEL_VERSION,
    )


@app.post("/predict")
def predict_endpoint():
    # silent=True gives None instead of raising when the body isn't json
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or "value" not in data:
        return jsonify(error="request body must be json with a 'value' field"), 400

    value = data["value"]
    # bool is a subclass of int in python, so True would pass the
    # number check below without this
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return jsonify(error="'value' must be a number"), 400

    return jsonify(input=value, prediction=predict(value))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
