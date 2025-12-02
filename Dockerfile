FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

ENV DEBIAN_FRONTEND=noninteractive
ENV UV_COMPILE_BYTECODE=1
ENV UV_CACHE_DIR=/home/appuser/.cache/uv

WORKDIR /app

RUN set -x && \
    groupadd --system --gid 1001 appuser && \
    useradd --system --uid 1001 --gid appuser --create-home --shell /bin/bash appuser && \
    mkdir -p /home/appuser/.cache/uv && \
    chown -R appuser:appuser /home/appuser && \
    chown -R appuser:appuser /app && \
    find / -perm /6000 -type f -exec chmod a-s {} \; || true

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
COPY server.py /app/server.py

RUN chmod +x /usr/local/bin/entrypoint.sh

ENTRYPOINT ["entrypoint.sh"]

CMD ["python", "server.py"]