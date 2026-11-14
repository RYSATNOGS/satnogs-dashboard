FROM docker:cli AS docker-cli
FROM python:slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Dashboard engine commands use the host daemon through the mounted socket.
COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker-cli /usr/local/libexec/docker/cli-plugins/docker-compose /usr/local/libexec/docker/cli-plugins/docker-compose

# Project env baked OUTSIDE any mount path (owner rule: no venv in the tree)
ENV UV_PROJECT_ENVIRONMENT=/opt/uv-env
WORKDIR /work
COPY pyproject.toml ./
RUN uv venv "$UV_PROJECT_ENVIRONMENT" && \
    uv pip install --no-cache --python "$UV_PROJECT_ENVIRONMENT" -r pyproject.toml
COPY app ./app
COPY scripts ./scripts

EXPOSE 8000
# app_factory: env reading + dashboard.db creation happen at server start
CMD ["/opt/uv-env/bin/uvicorn", "app.main:app_factory", "--factory", \
     "--host", "0.0.0.0", "--port", "8000"]
