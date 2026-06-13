#!/bin/bash

# 1. Đi vào thư mục con và bật Streamlit ở cổng 8501 (chạy ngầm bằng dấu &)
cd content-quality-checker
streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &

# 2. Bật tiếp Uvicorn Backend ở cổng 8000 mặc định
python -m uvicorn main:app --host 0.0.0.0 --port 8000
