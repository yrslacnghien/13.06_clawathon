import streamlit as st
import os
import sys

# Cấu hình giao diện Streamlit
st.set_page_config(page_title="VNG Content Quality Checker", page_icon="📝", layout="centered")
st.title("📝 VNG Content Quality Checker")
st.subheader("Trợ lý AI kiểm duyệt chất lượng bài đăng Social Media")
st.write("---")

caption = st.text_area("1. Nhập đoạn Caption bài viết cần kiểm tra:", placeholder="Dán văn bản bài đăng vào đây...", height=150)
uploaded_file = st.file_uploader("2. Tải lên hình ảnh Banner đi kèm (nếu có):", type=["png", "jpg", "jpeg"])
st.write("---")

if st.button("🚀 BẤT ĐẦU KIỂM DUYỆT QUALITY"):
    if not caption:
        st.warning("Vui lòng nhập đoạn Caption trước khi kiểm tra!")
    else:
        with st.spinner("AI Agent đang đối chiếu bộ quy chuẩn thương hiệu VNG..."):
            try:
                # Nhúng trực tiếp logic từ file core agent của bạn vào đây
                sys.path.append(os.path.abspath(os.path.dirname(__file__)))
                
                # Giả sử trong agent.py của bạn có hàm nhận caption và xử lý, ta gọi thẳng:
                from agent import check_content_direct  
                
                file_bytes = uploaded_file.getvalue() if uploaded_file else None
                result_output = check_content_direct(caption, file_bytes)
                
                st.success("🎉 Kiểm duyệt hoàn tất!")
                st.markdown("### 📊 Kết quả đánh giá từ AI Agent:")
                st.markdown(result_output)
            except Exception as e:
                # Phương án dự phòng: Nếu gọi trực tiếp bị lệch cấu trúc cũ, ta gọi qua API endpoint cục bộ
                try:
                    import requests
                    response = requests.post("http://127.0.0.1:8000/check", data={"caption": caption})
                    if response.status_code == 200:
                        st.success("🎉 Kiểm duyệt hoàn tất!")
                        st.markdown(response.json().get("output"))
                    else:
                        st.error("Không thể kết nối đến luồng xử lý AI nội bộ.")
                except:
                    st.error(f"Lỗi xử lý kiểm duyệt: {str(e)}")
