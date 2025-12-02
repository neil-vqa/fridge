#!/bin/sh
set -e

# This script runs as root at container startup.
echo "Entrypoint: Running as $(whoami)"

# Take ownership of the tmpfs directories created by the 'docker run' command.
echo "Entrypoint: Changing ownership of /tmp and cache directory..."
chown appuser:appuser /tmp
chown appuser:appuser /home/appuser/.cache/uv

# Drop privileges and execute the container's command (CMD).
# Use "$*" to join all arguments from the CMD into a single string,
# which is what the '-c' flag expects.
echo "Entrypoint: Dropping privileges and executing CMD..."
exec su appuser -c "$*"