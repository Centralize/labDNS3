# syntax=docker/dockerfile:1.7

ARG PYTHON_VERSION=3.12-slim
FROM python:${PYTHON_VERSION} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install minimal runtime deps
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -ms /bin/bash labdns
USER labdns
WORKDIR /app

# Copy and install
COPY --chown=labdns:labdns pyproject.toml README.md /app/
COPY --chown=labdns:labdns src /app/src

RUN pip install --no-cache-dir .

# Default zones directory inside container
VOLUME ["/zones"]

# Expose DNS UDP
EXPOSE 53/udp

# Healthcheck: ensure process is alive
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD pgrep -f "labdns" || exit 1

# Default command: serve zones from /zones
CMD ["labdns", "--log-level", "INFO", "start", "--zones-dir", "/zones", "--interface", "0.0.0.0", "--port", "53"]

