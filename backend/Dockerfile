FROM python:3.12.10-slim

# Install system dependencies + Prisma requirements
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy only dependency files first (better caching)
COPY requirements.txt .
COPY prisma/schema.prisma ./prisma/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Generate Prisma client
RUN prisma generate

# Copy application code
COPY . .

EXPOSE 10000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]