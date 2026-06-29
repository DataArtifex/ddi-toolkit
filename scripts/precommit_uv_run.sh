#!/bin/bash
if [ -n "$VIRTUAL_ENV" ]; then
  exec uv run --active "$@"
else
  exec uv run "$@"
fi
