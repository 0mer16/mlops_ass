# pinned to an exact python version (not latest) so the build doesn't
# change underneath us when a new python image comes out
FROM python:3.13.14-slim

# links the image in GHCR back to this repo
LABEL org.opencontainers.image.source="https://github.com/0mer16/mlops_ass"

# no .pyc files in the image, and logs go straight to docker logs
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# run as a normal user instead of root
RUN useradd --create-home appuser

# requirements first so the pip install layer stays cached
# when only the code changes
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py VERSION ./

USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" || exit 1

# build info passed in with --build-arg by the release workflow, so the
# image itself says which version and commit it came from.
# these are at the end on purpose: the commit and date change on every
# build, and anything after them would lose the layer cache
ARG APP_VERSION=dev
ARG GIT_COMMIT=unknown
ARG BUILD_DATE=unknown

LABEL org.opencontainers.image.title="student-ml-api" \
      org.opencontainers.image.description="Simple prediction API for the MLOps assignment" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${GIT_COMMIT}" \
      org.opencontainers.image.created="${BUILD_DATE}"

# gunicorn instead of the flask dev server. has to bind 0.0.0.0,
# 127.0.0.1 would only be reachable from inside the container
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--access-logfile", "-", "app:app"]
