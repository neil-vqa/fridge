#!/bin/sh
set -e

echo "Entrypoint: Running as $(whoami)"

echo "Entrypoint: Changing ownership of /tmp and cache directory..."
chown appuser:appuser /tmp
chown appuser:appuser /home/appuser/.cache/uv

echo "Entrypoint: Dropping privileges and executing CMD..."
exec su appuser -c "$*"