import streamlit as st
import requests
import subprocess
import os
import sys
import time

# Tuyệt chiêu: Tự động kích hoạt Backend Uvicorn chạy ngầm ở cổng 8500 nếu chưa có
if "BACKEND_STARTED" not in os.environ:
    os.environ["BACKEND_STARTED"] = "1"
    # Gọi Uvicorn chạy ngầm hoàn toàn bằng Python, lùi về cổng 8500
    subprocess.Popen([sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8500"], cwd="content-quality-checker")
    time.sleep(2) # Đợi 2 giây cho bộ não AI khởi động

# Cấu hình giao diện Streamlit ở cổng chính (sẽ được Railway tự gán)
st.set_page_config(page_title="VNG Content Quality Checker", page_icon="📝", layout="centered")
st.title("📝 VNG Content Quality Checker")
st.subheader("Trợ lý AI kiểm duyệt chất lượng bài đăng Social Media")
st.write("---")

caption = st.text_area("1. Nhập đoạn Caption bài viết cần kiểm tra:", placeholder="Dán văn bản bài đăng vào đây...", height=150)
uploaded_file = st.file_uploader("2. Tải lên hình ảnh Banner đi kèm (nếu có):", type=["png", "jpg", "jpeg"])
st.write("---")

if st.button("🚀 BẮT ĐẦU KIỂM DUYỆT QUALITY"):
    if not caption:
        st.warning("Vui lòng nhập đoạn Caption trước khi kiểm tra!")
    else:
        with st.spinner("AI đang quét ảnh và đối chiếu bộ quy chuẩn thương hiệu VNG..."):
            try:
                files = None
                if uploaded_file is not None:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                
                # Gọi vào cổng 8500 nội bộ
                backend_url = "http://127.0.0.1:8500/check" 
                data = {"caption": caption}
                
                response = requests.post(backend_url, data=data, files=files)
                
                if response.status_code == 200:
                    result = response.json()
                    st.success("🎉 Kiểm duyệt hoàn tất!")
                    st.markdown("### 📊 Kết quả đánh giá từ AI Agent:")
                    st.markdown(result.get("output", "Không có phản hồi từ AI."))
                else:
                    st.error(f"Lỗi kết nối Backend: {response.status_code}")
            except Exception as e:
                st.error(f"Không thể kết nối đến bộ não AI: {str(e)}")
