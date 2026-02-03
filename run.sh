#!/bin/bash
# Kariyer.net Finans - POS Komisyon Takip Sistemi
# Uygulamayı başlatmak için bu scripti çalıştırın

cd "$(dirname "$0")"

# Port 8501'i temizle (varsa)
lsof -ti:8501 | xargs kill -9 2>/dev/null

# Virtual environment aktive et
source .venv/bin/activate

# Streamlit uygulamasını başlat
echo "🚀 POS Komisyon Takip Sistemi başlatılıyor..."
echo "📍 http://localhost:8501"
echo ""
streamlit run src/dashboard/app.py --server.port 8501
