# Dependency Setup for Ticker Sentiment Analyzer

## Current Environment Issues

Attempting to install the required dependencies for the Ticker Sentiment Analyzer revealed that pip is not available in the current environment. This document provides instructions for setting up the necessary dependencies.

## Installation Steps

### 1. Install pip

First, install pip for Python 3:

```bash
# For Ubuntu/Debian
sudo apt-get update
sudo apt-get install python3-pip

# For CentOS/RHEL
sudo yum install python3-pip

# For macOS
brew install python3
```

### 2. Create Virtual Environment (Optional but Recommended)

Creating a virtual environment isolates the dependencies for this project:

```bash
# Install virtualenv
python3 -m pip install virtualenv

# Create a virtual environment
python3 -m virtualenv venv

# Activate the virtual environment
source venv/bin/activate  # On Linux/macOS
venv\Scripts\activate     # On Windows
```

### 3. Install Required Dependencies

Once pip is available, install the required dependencies:

```bash
python3 -m pip install -r sentiment_analyzer/requirements.txt
```

Or install each dependency individually:

```bash
python3 -m pip install pandas==2.2.0
python3 -m pip install numpy==1.26.0
python3 -m pip install pyarrow==14.0.1
python3 -m pip install redis==5.0.1
python3 -m pip install streamlit==1.32.0
python3 -m pip install plotly==5.18.0
python3 -m pip install matplotlib==3.8.0
python3 -m pip install requests==2.31.0
```

## Alternative: Docker Setup

If installing dependencies directly is problematic, consider using Docker:

1. Create a Dockerfile:

```Dockerfile
FROM python:3.9

WORKDIR /app

COPY sentiment_analyzer/requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# For Main Service
CMD ["python", "sentiment_analyzer/main.py"]
```

2. Build and run the Docker container:

```bash
docker build -t sentiment-analyzer .
docker run -p 8501:8501 sentiment-analyzer
```

## Testing After Installation

Once dependencies are installed, run the tests:

```bash
python3 -m unittest discover tests/sentiment_tests
```

## Troubleshooting

### Common Issues

1. **Permission Errors**: If you encounter permission issues, try:
   ```bash
   python3 -m pip install --user -r sentiment_analyzer/requirements.txt
   ```

2. **Incompatible Versions**: If you have version conflicts:
   ```bash
   python3 -m pip install --upgrade pip
   python3 -m pip install -r sentiment_analyzer/requirements.txt --ignore-installed
   ```

3. **Missing System Libraries**: Some packages may require system libraries:
   ```bash
   # For Ubuntu/Debian
   sudo apt-get install python3-dev build-essential
   ```

### Verifying Installation

To verify that all dependencies are correctly installed:

```bash
python3 -c "import pandas, numpy, pyarrow, redis, streamlit, plotly, matplotlib, requests; print('All dependencies successfully imported')"
```

This should output "All dependencies successfully imported" if all packages are installed correctly.