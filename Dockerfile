FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY run.py feeds.yaml gavel.png ./
ENV DB_FILE=/data/seen.db
VOLUME /data
CMD ["uv", "run", "--no-sync", "run.py"]
