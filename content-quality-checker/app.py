import streamlit as st
import os
import sys

# Khởi tạo giao diện Streamlit
st.set_page_config(page_title="VNG Content Quality Checker", page_icon="📝", layout="centered")
st.title("📝 VNG Content Quality Checker")
st.subheader("Trợ lý AI kiểm duyệt chất lượng bài đăng Social Media")
st.write("---")

# Nhúng code khởi tạo Agent trực tiếp trong Streamlit để không cần FastAPI nữa
@st.cache_resource
def init_ai_agent():
    try:
        # Import hàm hoặc class xử lý logic chính từ file agent của bạn
        # Giả định file agent của bạn có class hoặc hàm kiểm tra, ta import trực tiếp ở đây
        sys.path.append(os.path.abspath(os.path.dirname(__file__)))
        # Thay thế bằng hàm check thực tế trong source code của bạn (ví dụ: từ bộ core checker)
        from agent import CheckerAgent  # Hoặc hàm tương đương trong project của bạn
        return CheckerAgent()
    except Exception as e:
        st.error(f"Lỗi nạp bộ não AI Agent nội bộ: {str(e)}")
        return None

# Form nhập liệu trên giao diện
caption = st.text_area("1. Nhập đoạn Caption bài viết cần kiểm tra:", placeholder="Dán văn bản bài đăng vào đây...", height=150)
uploaded_file = st.file_uploader("2. Tải lên hình ảnh Banner đi kèm (nếu có):", type=["png", "jpg", "jpeg"])
st.write("---")

if st.button("🚀 BẮT ĐẦU KIỂM DUYỆT QUALITY"):
    if not caption:
        st.warning("Vui lòng nhập đoạn Caption trước khi kiểm tra!")
    else:
        with st.spinner("AI Agent đang quét ảnh và đối chiếu bộ quy chuẩn thương hiệu..."):
            try:
                # Gọi trực tiếp bộ não AI đã nạp thay vì gọi qua requests tốn thời gian
                # (Đoạn này mình giả lập lệnh gọi trực tiếp, bạn có thể chỉnh lại cho đúng hàm trong agent.py của bạn)
                from agent import check_content_direct  
                
                # Nếu file agent.py của bạn có hàm nhận caption và file, gọi thẳng nó:
                file_bytes = uploaded_file.getvalue() if uploaded_file else None
                result_output = check_content_direct(caption, file_bytes)
                
                st.success("🎉 Kiểm duyệt hoàn tất!")
                st.markdown("### 📊 Kết quả đánh giá từ AI Agent:")
                st.markdown(result_output)
                
            except Exception as e:
                # Phương án dự phòng: Nếu gọi trực tiếp bị lệch cấu trúc cũ, ta gọi sang file main.py (nếu vẫn chạy)
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
