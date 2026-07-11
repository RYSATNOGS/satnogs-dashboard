# Sibling convention: the container IS the environment (python:3.14-slim).
# Engine buttons shell out to `docker compose` against the sibling repos, so
# the image carries a static docker CLI + compose plugin that talk to the
# host daemon through the socket docker-compose.yml mounts in.
FROM python:3.14-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN set -eux; arch="$(uname -m)"; \
    python -c "import urllib.request as u,sys; u.urlretrieve(sys.argv[1], sys.argv[2])" \
        "https://download.docker.com/linux/static/stable/${arch}/docker-27.5.1.tgz" /tmp/docker.tgz; \
    tar -xzf /tmp/docker.tgz -C /tmp; \
    install -m 0755 /tmp/docker/docker /usr/local/bin/docker; \
    rm -rf /tmp/docker /tmp/docker.tgz; \
    mkdir -p /usr/local/lib/docker/cli-plugins; \
    python -c "import urllib.request as u,sys; u.urlretrieve(sys.argv[1], sys.argv[2])" \
        "https://github.com/docker/compose/releases/download/v2.32.4/docker-compose-linux-${arch}" \
        /usr/local/lib/docker/cli-plugins/docker-compose; \
    chmod 0755 /usr/local/lib/docker/cli-plugins/docker-compose

# Project env baked OUTSIDE any mount path (owner rule: no venv in the tree)
ENV UV_PROJECT_ENVIRONMENT=/opt/uv-env
WORKDIR /work
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY app ./app
COPY scripts ./scripts

EXPOSE 8000
# app_factory: env reading + dashboard.db creation happen at server start
CMD ["/opt/uv-env/bin/uvicorn", "app.main:app_factory", "--factory", \
     "--host", "0.0.0.0", "--port", "8000"]
