# Kariyer.net Finans - POS Komisyon Takip Sistemi
# Docker Image

FROM python:3.11-slim

WORKDIR /app

# Sistem bağımlılıkları
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Python bağımlılıkları
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyaları
COPY src/ ./src/
COPY config/ ./config/
COPY .streamlit/ ./.streamlit/

# Data klasörü
RUN mkdir -p data/raw data/processed data/output data/metadata data/uploads

# Port
EXPOSE 8501

# Healthcheck
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Başlatma komutu
ENTRYPOINT ["streamlit", "run", "src/dashboard/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
