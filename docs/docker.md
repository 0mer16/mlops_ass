# Docker: local build, inspection and build cache

All of this was run on my Windows laptop with Docker Desktop, using the code at tag `v1.0.0` unless stated otherwise.

## Building and running locally (Part 10)

```bash
docker build -t student-ml-api:1.0.0 .
docker run -d --name student-ml-api -p 5000:5000 student-ml-api:1.0.0
curl http://localhost:5000/health
```

```json
{"application":"student-ml-api","status":"healthy","version":"1.0.0"}
```

The version comes from the `VERSION` file baked into the image, so the container reports the version it was built from.

## Looking inside the container (Part 11)

`docker images`:

```
IMAGE                  ID             DISK USAGE   CONTENT SIZE   EXTRA
student-ml-api:1.0.0   5d91eccaa309        186MB         45.2MB   U
```

`docker ps`:

```
CONTAINER ID   IMAGE                  COMMAND                  CREATED          STATUS                    PORTS                                         NAMES
ce83662261b7   student-ml-api:1.0.0   "gunicorn --bind 0.0…"   50 seconds ago   Up 48 seconds (healthy)   0.0.0.0:5000->5000/tcp, [::]:5000->5000/tcp   student-ml-api
```

`(healthy)` comes from the `HEALTHCHECK` in the Dockerfile, which calls `/health` every 30 seconds from inside the container.

`docker logs student-ml-api`:

```
[2026-09-10 17:50:01 +0000] [1] [INFO] Starting gunicorn 26.2.0
[2026-09-10 17:50:01 +0000] [1] [INFO] Listening at: http://0.0.0.0:5000 (1)
[2026-09-10 17:50:01 +0000] [1] [INFO] Using worker: sync
[2026-09-10 17:50:01 +0000] [7] [INFO] Booting worker with pid: 7
[2026-09-10 17:50:01 +0000] [8] [INFO] Booting worker with pid: 8
172.17.0.1 - - [10/Sep/2026:17:50:05 +0000] "GET /health HTTP/1.1" 200 70 "-" "curl/8.21.0"
172.17.0.1 - - [10/Sep/2026:17:50:05 +0000] "POST /predict HTTP/1.1" 200 29 "-" "curl/8.21.0"
127.0.0.1 - - [10/Sep/2026:17:50:05 +0000] "GET /health HTTP/1.1" 200 70 "-" "Python-urllib/3.13"
```

The `172.17.0.1` lines are my curl requests coming in from the host through Docker's network. The `127.0.0.1` / `Python-urllib` lines are the health check running inside the container.

From `docker inspect student-ml-api`, these are the fields the assignment asks for:

| | Value | Where in `docker inspect` |
|---|---|---|
| Container ID | `ce83662261b760b1555463b337a9c2b47aaa2db6e32cecdddb6ace8603eed0a9` | `.Id` |
| Image ID | `sha256:5d91eccaa3090e0b493c12cf0a4cf07b0c66f7de46a520da50f41597b72a8925` | `.Image` |
| Exposed port | `5000/tcp`, published on host port 5000 | `.Config.ExposedPorts`, `.HostConfig.PortBindings` |
| Running command | `gunicorn --bind 0.0.0.0:5000 --workers 2 --access-logfile - app:app` | `.Config.Cmd` |
| Working directory | `/app` | `.Config.WorkingDir` |

It also shows `"User": "appuser"`, so the app isn't running as root.

`docker exec -it student-ml-api sh` opens a shell inside the container. Running a few commands in there:

```
$ pwd
/app
$ whoami
appuser
$ ls -la
-rwxr-xr-x 1 root root    7 Sep 10 17:41 VERSION
-rwxr-xr-x 1 root root 1499 Sep 10 17:41 app.py
-rwxr-xr-x 1 root root   32 Sep 10 17:41 requirements.txt
$ cat VERSION
1.0.0
$ pip list
Flask        3.1.3
gunicorn     26.2.0
```

Only the three files the Dockerfile copies are in `/app`. No tests, no `.git`, no `.venv`, which is `.dockerignore` and the specific `COPY` lines doing their job. pytest isn't installed either, because the image only uses `requirements.txt` and not `requirements-dev.txt`.

## Build cache experiment (Part 25)

I built the image once to fill the cache. Then I made one small change at a time (a comment appended to a file) and rebuilt with `docker build --progress=plain`, so I could see which steps said `CACHED`. The changes were reverted afterwards and never committed.

**Change only `app.py`**, 5.7s total:

```
#6 [2/6] WORKDIR /app                                      CACHED
#7 [3/6] RUN useradd --create-home appuser                 CACHED
#8 [4/6] COPY requirements.txt .                           CACHED
#9 [5/6] RUN pip install --no-cache-dir -r requirements.txt CACHED
#10 [6/6] COPY app.py VERSION ./                           DONE 0.4s
```

**Change only `requirements.txt`**, 19.1s total:

```
#6 [2/6] WORKDIR /app                                      CACHED
#7 [3/6] RUN useradd --create-home appuser                 CACHED
#8 [4/6] COPY requirements.txt .                           DONE 0.3s
#9 [5/6] RUN pip install --no-cache-dir -r requirements.txt DONE 11.8s
#10 [6/6] COPY app.py VERSION ./                           DONE 0.5s
```

(I lined the step output up to make it easier to read. The raw logs are longer.)

Docker caches each step. Once one step changes, it has to re-run every step after it. Changing `app.py` only affects the last `COPY`, so the slow `pip install` gets reused. Changing `requirements.txt` breaks the cache at step 4, so pip runs again, which is correct since the dependencies really did change.

To compare, I also built the `COPY . .` version the assignment mentions:

```dockerfile
COPY . .
RUN pip install -r requirements.txt
```

Changing only `app.py` with that Dockerfile, 16.7s total:

```
#6 [2/4] WORKDIR /app                                      CACHED
#7 [3/4] COPY . .                                          DONE 0.7s
#8 [4/4] RUN pip install --no-cache-dir -r requirements.txt DONE 10.0s
```

Now pip runs again even though no dependency changed. `COPY . .` copies `app.py` as well, so any code change invalidates that layer and everything after it, pip included.

So `COPY requirements.txt .` → `RUN pip install` → `COPY app.py .` is better because the code changes all the time and the dependencies hardly ever do. Here that's a 5.7s rebuild instead of about 17s. With a real ML project installing things like numpy or torch, pip can take minutes, and CI builds the image on every PR push, so the difference adds up quickly.

It's also why the OCI label build args sit at the very bottom of the Dockerfile. The commit and build date change on every release build, so if they were near the top, nothing below them could be cached.
