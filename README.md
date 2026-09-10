# student-ml-api

This is a small Flask API I built for the MLOps assignment. The "model" is just `value * 2`, since the point of the assignment is the workflow around it (branches, PRs, CI, Docker images, releases) and not the model itself.

## Endpoints

`GET /health` tells you the app is up and which version is running:

```json
{"status": "healthy", "application": "student-ml-api", "version": "1.0.0"}
```

`POST /predict` takes a number and returns the prediction:

```bash
curl -X POST http://localhost:5000/predict -H "Content-Type: application/json" -d "{\"value\": 10}"
```

```json
{"input": 10, "prediction": 20}
```

If `value` is missing, or isn't a number (a string, null, true/false, a list), you get a 400 with an `error` message instead of a crash.

The version shown in `/health` is read from the `VERSION` file, so that file is the only thing that needs changing when I bump the version.

## Running it locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
python app.py
```

It starts on http://localhost:5000.

`requirements.txt` only has what the app needs to run (Flask and gunicorn). `requirements-dev.txt` pulls that in and adds pytest. I split them so pytest doesn't get installed into the Docker image.

## Tests

```bash
pytest -v
```

The tests cover the health endpoint, a normal prediction, a float input, a missing `value`, a body that isn't JSON, and a few invalid values.

## Docker

```bash
docker build -t student-ml-api:1.0.0 .
docker run -d --name student-ml-api -p 5000:5000 student-ml-api:1.0.0
curl http://localhost:5000/health
```

Some notes on the Dockerfile:

- The base image is pinned to `python:3.13.14-slim`, not `latest`, so the build doesn't quietly change when a new Python image is released.
- `requirements.txt` is copied and installed before `app.py`. Docker caches each step, so if I only change the code, the pip install step is reused and the rebuild is fast.
- Inside the container the app runs with gunicorn instead of the Flask dev server, and it binds to `0.0.0.0`. If it bound to `127.0.0.1` it would only be reachable from inside the container, and `-p 5000:5000` wouldn't help.
- It runs as a normal user (`appuser`), not root.

## How changes get in

Nothing gets committed straight to `main`. Every change goes on a `feature/...` branch and gets a pull request, and the CI workflow (`.github/workflows/ci.yml`) runs on the PR. It runs the tests, then builds the Docker image and checks `/health` on a running container. The image is only built there, never pushed.

`main` is protected, so a PR can't be merged until both CI jobs (`test` and `docker-build`) have passed. There's also a PR template (`.github/pull_request_template.md`) so every PR has the same sections.

## Releases

Images only get published when I push a version tag on `main`:

```bash
git checkout main
git pull
git tag v1.0.0
git push origin v1.0.0
```

That triggers `.github/workflows/release.yml`, which:

1. runs the tests again
2. strips the `v` from the tag to get the version (`v1.0.0` becomes `1.0.0`), so the version isn't typed anywhere in the workflow
3. checks that the tag matches the `VERSION` file and stops if it doesn't
4. logs in to GitHub Container Registry with the `GITHUB_TOKEN` that Actions gives each run, so no password is stored in the repo
5. builds the image, tags it with the version and `latest`, and pushes both

The image ends up at `ghcr.io/0mer16/student-ml-api`, so anyone can run a specific version without cloning the repo:

```bash
docker pull ghcr.io/0mer16/student-ml-api:1.0.0
docker run -d --name student-ml-api -p 5000:5000 ghcr.io/0mer16/student-ml-api:1.0.0
```
