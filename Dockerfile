FROM node:24.19.0-bookworm-slim AS frontend-build
WORKDIR /web
RUN npm install --global pnpm@11.19.0
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY frontend/ ./
RUN pnpm build

FROM python:3.12.14-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    OMP_NUM_THREADS=4 \
    OPENBLAS_NUM_THREADS=4
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir --require-hashes -r requirements.txt \
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
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8501/api/health', timeout=4)"
CMD ["sh", "-c", "python -m scripts.check && exec python -m uvicorn housing_app.api:app --host 0.0.0.0 --port 8501 --proxy-headers --forwarded-allow-ips 127.0.0.1"]
