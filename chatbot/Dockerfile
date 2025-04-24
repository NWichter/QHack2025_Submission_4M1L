# Use an appropriate base image
FROM python:3.10-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Install Python dependencies in layers
COPY requirements.txt /app/

# Install dependencies with pip
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy your application code
COPY . /app/

EXPOSE 8080

CMD ["python", "-m", "chainlit", "run", "app.py", "--host", "0.0.0.0", "--port", "8080"]