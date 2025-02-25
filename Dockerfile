FROM python:3.12
WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Environment variables for configuration
# (These can be overridden at runtime via `docker run -e VAR=...`)
ENV RABBITMQ_HOST=rabbit
ENV RABBITMQ_USER=guest
ENV RABBITMQ_PASS=guest
ENV RABBITMQ_QUEUE=now_playing
ENV RDS_ENCODER_HOST=smartgen-mini
ENV RDS_ENCODER_PORT=1024

# Default command to run the consumer
CMD [ "python", "-u", "main.py" ]

# Build: `docker build -t wbor-rds-encoder .`
# Run: `docker run -d --name wbor-rds-encoder --restart unless-stopped wbor-rds-encoder`