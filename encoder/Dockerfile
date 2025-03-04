FROM python:3.12

# Ensure python doesn't buffer logs
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install curl and clean up
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Default command to run the consumer
CMD [ "python", "-u", "rds.py" ]