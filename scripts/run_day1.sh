#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-P36}"
VENV_PY="$VENV_DIR/bin/python"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "[ERROR] Khong tim thay python3."
  exit 1
fi

if [ ! -x "$VENV_PY" ]; then
  echo "[INFO] Tao moi truong ao $VENV_DIR (system-site-packages) cho Jetson..."
  "$PYTHON_BIN" -m venv "$VENV_DIR" --system-site-packages
fi

echo "[INFO] Kiem tra phien ban Python..."
"$VENV_PY" -c "import sys; print('[INFO] Python:', sys.version)"

echo "[INFO] Kiem tra thu vien bat buoc..."
if ! "$VENV_PY" -c "import cv2, yaml, numpy, psutil" >/dev/null 2>&1; then
  echo "[INFO] Cai dat cac thu vien Python can thiet..."
  "$VENV_PY" -m pip install --upgrade pip setuptools wheel
  "$VENV_PY" -m pip install -r requirements-jetson.txt
fi

if ! "$VENV_PY" -c "import cv2" >/dev/null 2>&1; then
  echo "[ERROR] Khong import duoc cv2 trong moi truong hien tai."
  echo "[HINT] Tren Jetson, hay cai goi he thong: sudo apt install -y python3-opencv"
  exit 1
fi

if ! "$VENV_PY" -c "import cv2; import numpy as np; _ = cv2.getBuildInformation(); print('ok')" >/dev/null 2>&1; then
  echo "[ERROR] Co the dang xung dot giua numpy va OpenCV he thong."
  echo "[HINT] Thu go numpy pip trong $VENV_DIR va dung numpy he thong hoac cai lai numpy tu requirements-jetson.txt"
  exit 1
fi

echo "[INFO] Chay ung dung Day 1..."
"$VENV_PY" -m src.app.main
