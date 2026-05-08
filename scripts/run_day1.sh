#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "[ERROR] Khong tim thay python3."
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "[INFO] Tao moi truong ao .venv (system-site-packages) cho Jetson..."
  "$PYTHON_BIN" -m venv .venv --system-site-packages
fi

VENV_PY=".venv/bin/python"

echo "[INFO] Kiem tra phien ban Python..."
"$VENV_PY" -c "import sys; print('[INFO] Python:', sys.version)"

echo "[INFO] Kiem tra thu vien bat buoc..."
if ! "$VENV_PY" -c "import cv2, yaml, numpy, psutil" >/dev/null 2>&1; then
  echo "[INFO] Cai dat cac thu vien Python can thiet..."
  "$VENV_PY" -m pip install --upgrade pip setuptools wheel
  "$VENV_PY" -m pip install numpy==1.19.5 PyYAML==6.0.1 psutil==5.9.5
fi

if ! "$VENV_PY" -c "import cv2" >/dev/null 2>&1; then
  echo "[ERROR] Khong import duoc cv2 trong moi truong hien tai."
  echo "[HINT] Tren Jetson, hay cai goi he thong: sudo apt install -y python3-opencv"
  exit 1
fi

echo "[INFO] Chay ung dung Day 1..."
"$VENV_PY" -m src.app.main
