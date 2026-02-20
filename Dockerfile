# syntax=docker/dockerfile:1

ARG UV_VERSION=0.10.4
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM debian:13-slim AS build
# Don't write .pyc bytecode files. These speed up imports when the program is
# loaded. There's no point doing that in a container where they'll never be
# persisted across restarts.
ENV UV_PYTHON_INSTALL_DIR=/python PYTHONDONTWRITEBYTECODE=true
COPY --from=uv /uv /uvx /bin/

WORKDIR /app
ADD . .
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --no-dev --no-cache --no-editable --python-preference only-managed

FROM gcr.io/distroless/cc-debian13:nonroot AS image
LABEL org.opencontainers.image.description="A Crossplane composition function to enforce naming conventions"
WORKDIR /app

# Copy python interpreter and the application from the builder
COPY --from=build --chown=python:python /python /python
COPY --from=build --chown=nonroot:nonroot /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:${PATH}"
EXPOSE 9443
USER nonroot:nonroot
ENTRYPOINT ["function"]
