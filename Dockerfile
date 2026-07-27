# syntax=docker/dockerfile:1.7
ARG PYTHON_IMAGE=python:3.12-slim@sha256:57cd7c3a7a273101a6485ba99423ee568157882804b1124b4dd04266317710de

FROM ${PYTHON_IMAGE} AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1
WORKDIR /build
COPY pyproject.toml requirements-api.lock README.md ./
COPY humorvibes ./humorvibes
COPY formats.py humor_mesh.py mesh_signals.py ./
RUN python -m pip wheel --wheel-dir /wheels --requirement requirements-api.lock \
    && python -m pip wheel --wheel-dir /wheels --no-deps .

FROM ${PYTHON_IMAGE} AS runtime
ARG VERSION=0.7.1
ARG VCS_REF=""
ARG BUILD_DATE=""
LABEL org.opencontainers.image.title="HumorVibes Research API" \
      org.opencontainers.image.description="Validated LLM, embedding, and humor-research integration API" \
      org.opencontainers.image.source="https://github.com/aidonerightcorp/humorvibes-jestry" \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.licenses="Apache-2.0"
ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HUMORVIBES_HOST=0.0.0.0 \
    HUMORVIBES_PORT=8080 \
    HUMORVIBES_LLM_DEFAULT=offline \
    HUMORVIBES_EMBEDDING_DEFAULT=hash:128
RUN groupadd --gid 10001 humorvibes \
    && useradd --uid 10001 --gid 10001 --no-create-home --home-dir /app --shell /usr/sbin/nologin humorvibes
WORKDIR /app
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-index --find-links=/wheels "humorvibes-research[api,telemetry]" \
    && rm -rf /wheels
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=4s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health/live', timeout=3).read()"]
ENTRYPOINT ["humorvibes-api"]
