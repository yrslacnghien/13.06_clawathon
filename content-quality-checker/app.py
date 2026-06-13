import streamlit as st
import os
import sys

# Cấu hình giao diện Streamlit
st.set_page_config(page_title="VNG Content Quality Checker", page_icon="📝", layout="centered")
st.title("📝 VNG Content Quality Checker")
st.subheader("Trợ lý AI kiểm duyệt chất lượng bài đăng Social Media")
st.write("---")

# Nhập đoạn văn bản và tải ảnh
caption = st.text_area("1. Nhập đoạn Caption bài viết cần kiểm tra:", placeholder="Dán văn bản bài đăng vào đây...", height=150)
uploaded_file = st.file_uploader("2. Tải lên hình ảnh Banner đi kèm (nếu có):", type=["png", "jpg", "jpeg"])
st.write("---")

if st.button("🚀 BẮT ĐẦU KIỂM DUYỆT QUALITY"):
    if not caption:
        st.warning("Vui lòng nhập đoạn Caption trước khi kiểm tra!")
    else:
        with st.spinner("AI Agent đang đối chiếu bộ quy chuẩn thương hiệu VNG..."):
            try:
                # Import trực tiếp logic từ file agent của bạn để xử lý tại chỗ không qua API
                sys.path.append(os.path.abspath(os.path.dirname(__file__)))
                from agent import check_content_direct  # Đảm bảo hàm này có sẵn trong agent.py của bạn
                
                file_bytes = uploaded_file.getvalue() if uploaded_file else None
                result_output = check_content_direct(caption, file_bytes)
                
                st.success("🎉 Kiểm duyệt hoàn tất!")
                st.markdown("### 📊 Kết quả đánh giá từ AI Agent:")
                st.markdown(result_output)
            except Exception as e:
                st.error(f"Lỗi xử lý kiểm duyệt: {str(e)}")
