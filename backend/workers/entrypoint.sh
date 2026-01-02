#!/bin/bash
set -e

# Fix docker socket permissions if it exists
if [ -S /var/run/docker.sock ]; then
    chmod 666 /var/run/docker.sock
fi

# Run the command passed to the container
exec "$@"
