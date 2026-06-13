import streamlit as st
import os
import sys

# Cấu hình giao diện chuẩn chỉnh của tool kiểm duyệt
st.set_page_config(page_title="VNG Content Quality Checker", page_icon="📝", layout="centered")
st.title("📝 VNG Content Quality Checker")
st.subheader("Trợ lý AI kiểm duyệt chất lượng bài đăng Social Media")
st.write("---")

# Thêm đường dẫn để Streamlit đọc được file core agent của bạn
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

# Nạp bộ não AI Agent trực tiếp bằng tính năng cache để không bị nạp lại mỗi lần bấm nút
@st.cache_resource
def load_checker_agent():
    try:
        # Ở đây ta import thẳng class hoặc hàm xử lý core trong agent.py của bạn
        # Ví dụ giả định bạn có hàm check_content_direct hoặc class Agent trong core
        from agent import check_content_direct
        return check_content_direct
    except Exception as e:
        st.error(f"Lỗi khởi tạo bộ não AI Agent: {str(e)}")
        return None

check_fn = load_checker_agent()

# Form tương tác nhập liệu
caption = st.text_area("1. Nhập đoạn Caption bài viết cần kiểm tra:", placeholder="Dán văn bản bài đăng vào đây...", height=150)
uploaded_file = st.file_uploader("2. Tải lên hình ảnh Banner đi kèm (nếu có):", type=["png", "jpg", "jpeg"])
st.write("---")

if st.button("🚀 BẤT ĐẦU KIỂM DUYỆT QUALITY"):
    if not caption:
        st.warning("Vui lòng nhập đoạn Caption trước khi kiểm tra!")
    else:
        with st.spinner("AI Agent đang đối chiếu dữ liệu với bộ quy chuẩn thương hiệu..."):
            if check_fn:
                try:
                    # Đọc file ảnh dưới dạng bytes nếu có
                    file_bytes = uploaded_file.getvalue() if uploaded_file else None
                    
                    # Gọi trực tiếp bộ xử lý AI core tại chỗ, bỏ qua mọi tầng API trung gian
                    result_output = check_fn(caption, file_bytes)
                    
                    st.success("🎉 Kiểm duyệt hoàn tất!")
                    st.markdown("### 📊 Kết quả đánh giá từ AI Agent:")
                    st.markdown(result_output)
                except Exception as e:
                    st.error(f"Lỗi trong quá trình AI phân tích văn bản: {str(e)}")
            else:
                st.error("Bộ não AI chưa được nạp thành công vào hệ thống.")
