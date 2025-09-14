# Use the official Python image.
FROM python:3.11-slim

# Set environment variables.
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV UV_LINK_MODE=copy
ENV EDITOR=vim
ENV PATH="/usr/local/go/bin:${PATH}"

# Install curl & git
RUN apt-get update && apt-get install -y curl git vim && rm -rf /var/lib/apt/lists/*

# Install Go
ARG GO_VERSION=1.22.0
RUN curl -fsSL "https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz" | tar -C /usr/local -xz

# Install Go-Task to a global path
RUN GOBIN=/usr/local/bin go install github.com/go-task/task/v3/cmd/task@latest

# Install uv
RUN pip install uv
RUN uv pip install --system pre-commit

# Create a non-root user
RUN addgroup --gid 1001 vscode && adduser --uid 1001 --gid 1001 --shell /bin/bash --disabled-password vscode
USER vscode

# Set the working directory
WORKDIR /home/vscode/workspace

# Copy the rest of the application code
COPY . .
