# student-ml-api

This is a small Flask API I built for the MLOps assignment. The "model" is just `value * 2`, since the point of the assignment is the workflow around it (branches, PRs, CI, Docker images, releases) and not the model itself.

## Endpoints

`GET /health` tells you the app is up and which versions are running:

```json
{
  "status": "healthy",
  "application": "student-ml-api",
  "application_version": "1.1.0",
  "model_version": "model-1"
}
```

Up to 1.0.0 this just had a single `version` field. In 1.1.0 I split it into `application_version` (the code) and `model_version` (the model). In a real ML service those change separately: you can retrain the model without touching the code, or change the code and keep the same model. With one field you couldn't tell which of the two had changed.

`POST /predict` takes a number and returns the prediction:

```bash
curl -X POST http://localhost:5000/predict -H "Content-Type: application/json" -d "{\"value\": 10}"
```

```json
{"input": 10, "prediction": 20}
```

If `value` is missing, or isn't a number (a string, null, true/false, a list), you get a 400 with an `error` message instead of a crash.

The `application_version` in `/health` is read from the `VERSION` file, so that file is the only thing that needs changing when I bump the version.

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
5. builds the image with the version, commit and build date passed in as build args
6. tags it three ways (the version, `latest`, and the short commit sha, like `8c371d2`) and pushes all three
7. writes the tag, commit and image digest to the run's summary page

The image ends up at `ghcr.io/0mer16/student-ml-api`, so anyone can run a specific version without cloning the repo:

```bash
docker pull ghcr.io/0mer16/student-ml-api:1.0.0
docker run -d --name student-ml-api -p 5000:5000 ghcr.io/0mer16/student-ml-api:1.0.0
```

### Finding out where an image came from

Each release image has OCI labels with the version, the full commit sha, the build date and the repo URL:

```bash
docker image inspect --format "{{json .Config.Labels}}" ghcr.io/0mer16/student-ml-api:1.1.0
```

So even if someone only has the image, they can see which commit built it. A local `docker build` without the build args just gets `dev` and `unknown` in those labels, so you can tell it apart from a real release.

The sha tag does the same job from the other side. `latest` moves every time there's a release, and in theory a version tag could be pushed again, but the sha tag only ever points at the image built from that one commit. If I'm looking at a commit in the git history and want the exact image for it, I can pull `student-ml-api:<short sha>` without having to work out which version it went into.

The labels are at the bottom of the Dockerfile on purpose. The commit and date change on every build, and Docker rebuilds every step after the first one that changes, so putting them at the top would throw away the cached pip install every time.

## Rolling back

If a release has a problem, go back to the previous image. No code change or rebuild needed:

```bash
docker stop student-ml-api
docker container remove student-ml-api
docker run -d --name student-ml-api -p 5000:5000 ghcr.io/0mer16/student-ml-api:1.0.0
```

## Assignment write-ups

The notes and evidence for each part of the assignment are in `docs/`:

- [docs/git-workflow.md](docs/git-workflow.md): how PRs got into `main`, the CI failure I caused on purpose, branch protection settings, merge strategy, and why CI and release are separate
- [docs/docker.md](docs/docker.md): local build and run, `docker inspect` / `logs` / `exec` output, and the build cache experiment
- [docs/releases.md](docs/releases.md): the two releases, registry tags and digests, pulling instead of rebuilding, rollback, and the full traceability chain for 1.1.0
- [docs/failure-analysis.md](docs/failure-analysis.md): four problems I reproduced on purpose (plus one I didn't), with symptom, cause, evidence and fix
