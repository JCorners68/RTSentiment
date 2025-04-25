FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
# Make sure pandas and pyarrow dependencies are correctly installed
RUN pip install --no-cache-dir pandas>=2.0.0 pyarrow>=12.0.0

# Copy application code
COPY . .

# Create data directories
RUN mkdir -p data/output data/cache data/logs

# Set environment variables
ENV PYTHONUNBUFFERED=1

CMD ["python", "main.py"]