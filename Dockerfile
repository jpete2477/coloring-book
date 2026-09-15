FROM python:3.12-slim

RUN pip install --no-cache-dir uv

WORKDIR /app
COPY pyproject.toml ./
COPY app app
COPY cli cli
COPY templates templates
RUN uv sync --no-dev

EXPOSE 8000
CMD ["uv", "run", "bookfactory", "serve", "--host", "0.0.0.0", "--port", "8000"]
