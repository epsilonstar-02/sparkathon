FROM python:3.12.10-slim


RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app


COPY requirements.txt .
COPY prisma/schema.prisma ./prisma/


RUN pip install --no-cache-dir -r requirements.txt


RUN prisma generate

COPY . .

EXPOSE 10000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"]