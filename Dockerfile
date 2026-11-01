# Web app image. Build and run with `docker compose up -d --build` (see readme).

# Build stage: uv installs the dependencies and the app into /app/.venv
FROM python:3.13-slim AS build

COPY --from=ghcr.io/astral-sh/uv:0.11.0 /uv /bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies first, so code changes don't reinstall them
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY readme.md ./
COPY bankcheck ./bankcheck
RUN uv sync --locked --no-dev

# Final image: only Python and the venv. Neither uv nor pip are needed to run the app,
# and their bundled libraries (Rust crates in uv, urllib3/msgpack/setuptools in pip)
# are where the image's vulnerabilities came from.
FROM python:3.13-slim

RUN rm -rf /usr/local/bin/pip* \
        /usr/local/lib/python3.13/site-packages/pip* \
        /usr/local/lib/python3.13/ensurepip/_bundled

WORKDIR /app
COPY --from=build /app /app

# All the data (history, uploads) lives in the /data volume
ENV PATH="/app/.venv/bin:$PATH" \
    BANKCHECK_DATA_DIR=/data
RUN useradd --system --uid 1000 --no-create-home bankcheck \
    && mkdir /data && chown bankcheck /data
USER bankcheck
VOLUME /data

EXPOSE 8000
HEALTHCHECK --interval=1m --timeout=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/static/style.css')"
CMD ["bankcheck-web", "--host", "0.0.0.0", "--port", "8000"]
