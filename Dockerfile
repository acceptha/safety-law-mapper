# Build: docker build -t safety-law-mapper .
# Run:   docker run --rm -p 8000:8000 safety-law-mapper
FROM python:3.13-slim

# The dataset is baked into the image. It is a build artifact that changes by
# pull request, so a running container never needs to fetch or write it.
WORKDIR /app

COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY data/ ./data/
COPY schemas/ ./schemas/

RUN pip install --no-cache-dir ".[api]"

# Fail the build, not production, if the bundled data is broken.
RUN slm validate

# Non-root: the API is read-only and has no reason to own anything.
RUN useradd --create-home --uid 10001 app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

CMD ["slm-serve", "--host", "0.0.0.0", "--port", "8000"]
