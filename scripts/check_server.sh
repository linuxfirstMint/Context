#!/bin/bash

if ! curl -s http://127.0.0.1:8000/ > /dev/null; then
  echo "Error: FastAPI server is not running on http://127.0.0.1:8000/"
  echo "Please start the server using 'task run' in another terminal."
  exit 1
fi
