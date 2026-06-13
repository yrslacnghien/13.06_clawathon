import streamlit as st
import os
import sys

st.set_page_config(page_title="VNG Content Quality Checker", page_icon="📝", layout="centered")
st.title("📝 VNG Content Quality Checker")
st.subheader("Trợ lý AI kiểm duyệt chất lượng bài đăng Social Media")
st.write("---")

# Ép nạp thẳng bộ não AI Agent vào Streamlit
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
try:
    from agent import check_content_direct
except Exception as e:
    st.error(f"Lỗi nạp Agent: {str(e)}")
    check_content_direct = None

caption = st.text_area("1. Nhập đoạn Caption bài viết cần kiểm tra:", placeholder="Dán văn bản bài đăng vào đây...", height=150)
uploaded_file = st.file_uploader("2. Tải lên hình ảnh Banner đi kèm (nếu có):", type=["png", "jpg", "jpeg"])
st.write("---")

if st.button("🚀 BẮT ĐẦU KIỂM DUYỆT QUALITY"):
    if not caption:
        st.warning("Vui lòng nhập đoạn Caption trước khi kiểm tra!")
    elif check_content_direct is None:
        st.error("Bộ não AI Agent chưa được nạp.")
    else:
        with st.spinner("AI Agent đang đối chiếu bộ quy chuẩn thương hiệu VNG..."):
            try:
                file_bytes = uploaded_file.getvalue() if uploaded_file else None
                result_output = check_content_direct(caption, file_bytes)
                st.success("🎉 Kiểm duyệt hoàn tất!")
                st.markdown("### 📊 Kết quả đánh giá từ AI Agent:")
                st.markdown(result_output)
            except Exception as e:
                st.error(f"Lỗi xử lý: {str(e)}")
