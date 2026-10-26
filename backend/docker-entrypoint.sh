#!/bin/sh
set -e
alembic upgrade head || true
exec "$@"
