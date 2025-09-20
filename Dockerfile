# syntax=docker/dockerfile:1

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VIRTUALENVS_CREATE=0

# System dependencies required for Tkinter, rendering and PDF processing
RUN apt-get update \ 
    && apt-get install -y --no-install-recommends \
        python3-tk \
        tk-dev \
        libgl1 \
        libglu1-mesa \
        libx11-6 \
        libxext6 \
        libsm6 \
        libxrender1 \
        libgdk-pixbuf2.0-0 \
        libgtk-3-0 \
        libcanberra-gtk3-module \
        ghostscript \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first to leverage layer caching
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

ENV PYTHONPATH=/app/app/src

# Default command runs the Tkinter client; requires an X server on the host
CMD ["python", "app/src/app/gui_client.py"]
