#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

source /etc/os-release
if [[ "${ID:-}" != "ubuntu" || "${VERSION_ID:-}" != "24.04" ]]; then
  echo "RepoPilot supports Ubuntu 24.04 WSL2; found ${PRETTY_NAME:-unknown}." >&2
  exit 1
fi

if ! command -v conda >/dev/null 2>&1; then
  echo "conda is required. Initialize Miniconda for bash first." >&2
  exit 1
fi

if conda env list | awk '{print $1}' | grep -Fxq repopilot; then
  conda env update -n repopilot -f environment.yml --prune
else
  conda env create -f environment.yml
fi

if ! docker version >/dev/null 2>&1; then
  echo "Docker is unavailable in this distro. Enable Docker Desktop WSL integration for Ubuntu-24.04." >&2
  exit 1
fi
docker build -t repopilot-runner:py312 -f docker/Dockerfile .

echo "Bootstrap complete. Run: conda activate repopilot"
