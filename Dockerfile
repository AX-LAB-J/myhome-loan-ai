# syntax=docker/dockerfile:1.7
# Build:  docker build --platform linux/amd64 -t housing-side .
# The image holds code and the built UI only. data/, models/ and .env are mounted at run time.

FROM node:24.19.0-bookworm-slim AS frontend-build
WORKDIR /web
RUN npm install --global pnpm@11.19.0
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
# Copy sources only: re-copying package.json would make pnpm think node_modules is stale.
COPY frontend/index.html frontend/tsconfig.json frontend/vite.config.ts ./
COPY frontend/src ./src
RUN pnpm build

FROM python:3.12.14-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    OMP_NUM_THREADS=4 \
    OPENBLAS_NUM_THREADS=4 \
    # Trust X-Forwarded-* only from these proxies (compose.aws.yaml sets the Caddy network).
    FORWARDED_ALLOW_IPS=127.0.0.1
WORKDIR /app
COPY requirements.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --require-hashes -r requirements.txt \
    && pip check \
    && groupadd --gid 10001 app \
    && useradd --uid 10001 --gid app --no-create-home app
COPY housing_app/ ./housing_app/
COPY scripts/__init__.py scripts/check.py ./scripts/
COPY reports/model_evaluation.json reports/data_audit.json ./reports/
COPY --from=frontend-build /web/dist ./frontend/dist/
RUN mkdir -p data models && chown -R app:app /app
USER app
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/api/health', timeout=4)"
CMD ["sh", "-c", "python -m scripts.check && exec python -m uvicorn housing_app.api:app --host 0.0.0.0 --port 8501 --proxy-headers --no-server-header --timeout-graceful-shutdown 20"]
