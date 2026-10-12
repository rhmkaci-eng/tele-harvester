FROM python:3.11-slim

# Prevent Python from writing .pyc files and buffer std streams
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Create volume mounts for persistent sessions and output logs
VOLUME ["/app/data", "/app/logs"]

# Single instance lock port
EXPOSE 58921

CMD ["python", "main.py"]
