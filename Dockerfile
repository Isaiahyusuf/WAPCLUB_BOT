# Use official Python image as base
FROM python:3.11-slim

WORKDIR /app

COPY . .

# Install dependencies
RUN pip install --upgrade pip \
    && pip install python-telegram-bot psycopg2 requests

# Expose port (if needed for health checks)
EXPOSE 8080

CMD ["python", "main.py"]
