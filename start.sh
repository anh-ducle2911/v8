#!/bin/bash
# HPL Dispatcher — Khởi động nhanh (không cần Docker)
set -e

echo "========================================="
echo "  HPL AI Dispatching & Routing Engine v3"
echo "  Hòa Phát Logistics · Control Tower"
echo "========================================="

# Kiểm tra Python
if ! command -v python3 &>/dev/null; then
  echo "❌ Chưa cài Python 3. Tải tại https://python.org"
  exit 1
fi

# Tạo virtual env nếu chưa có
if [ ! -d "venv" ]; then
  echo "📦 Đang tạo môi trường Python..."
  python3 -m venv venv
fi

source venv/bin/activate

echo "📥 Đang cài thư viện..."
pip install -q -r requirements.txt

echo ""
echo "✅ Sẵn sàng! Mở trình duyệt tại: http://localhost:8000"
echo "   (Ctrl+C để dừng)"
echo ""

python app.py
