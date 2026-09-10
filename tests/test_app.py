import pytest

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200

    data = response.get_json()
    assert data["status"] == "healthy"
    assert data["application"] == "student-ml-api"
    assert data["application_version"] == "1.0.0"
    # the old field name is gone now that there are two versions
    assert "version" not in data


def test_health_reports_model_version(client):
    data = client.get("/health").get_json()
    assert data["model_version"] == "model-1"


def test_predict_success(client):
    response = client.post("/predict", json={"value": 10})
    assert response.status_code == 200
    assert response.get_json() == {"input": 10, "prediction": 20}


def test_predict_with_float(client):
    response = client.post("/predict", json={"value": 2.5})
    assert response.status_code == 200
    assert response.get_json()["prediction"] == 5.0


def test_predict_missing_value(client):
    response = client.post("/predict", json={})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_predict_without_json_body(client):
    response = client.post("/predict", data="hello", content_type="text/plain")
    assert response.status_code == 400


@pytest.mark.parametrize("bad_value", ["abc", None, True, [1, 2], {"x": 1}])
def test_predict_invalid_value(client, bad_value):
    response = client.post("/predict", json={"value": bad_value})
    assert response.status_code == 400
    assert response.get_json()["error"] == "'value' must be a number"
