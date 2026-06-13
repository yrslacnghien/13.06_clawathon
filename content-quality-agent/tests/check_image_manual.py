"""Manual image + caption consistency check.

Set IMAGE_PATH and CAPTION, then run:
    python content-quality-agent/tests/check_image_manual.py

Optional:
    python content-quality-agent/tests/check_image_manual.py http://localhost:8000
"""

import json
import mimetypes
import sys
from pathlib import Path

import requests


BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"


# Put your local image path here.
IMAGE_PATH = Path(__file__).parent / "test_image" / "test.jpg"


# Paste the caption/post text here.
CAPTION = """
SOCIAL CHALLENGE] MY IRONMAN JOURNEY: TÁI HIỆN HÌNH ẢNH CHÍNH MÌNH Ở MÙA IRONMAN ĐẦU TIÊN 🎽
👉 Thời gian tham gia: 02/05 - 12/05/2025

Mỗi mùa giải IRONMAN trở lại, những “người sắt” lại bước vào đường đua với quyết tâm chinh phục những mục tiêu mới. Nhưng những khoảnh khắc của mùa giải đầu tiên, lần đầu đứng trước vạch xuất phát, lần đầu hoàn thành một chặng đua đầy thách thức, luôn để lại những cảm xúc khó quên nhất.

Hãy cùng Life at VNG nhìn lại hành trình IRONMAN của bạn qua Social Challenge “My IRONMAN Journey” - từ cột mốc khởi đầu cho đến tinh thần sẵn sàng chinh phục những thử thách mới trong giải VNG IRONMAN Việt Nam 2025 năm nay.

📅 Thời gian tham gia: 02/05/2025 - 12/05/2025
👥 Đối tượng tham gia: Vận động viên đã từng tham gia các mùa IRONMAN
🔗 Nền tảng: Facebook, Instagram, Threads, TikTok hoặc myVNG (kênh thông tin nội bộ dành riêng cho nhân viên của VNG)

🎁 Cơ cấu giải thưởng: Combo Bình giữ nhiệt VNG + Khăn tắm VNG IRONMAN Việt Nam 2026 dành cho 30 bài chia sẻ hợp lệ và may mắn nhất

🎯 Thể lệ tham gia:
1️⃣ Bước 1: Chọn một ảnh từ mùa IRONMAN bạn từng tham gia (ưu tiên mùa đầu tiên). Tái hiện hình ảnh đó qua khoảnh khắc tập luyện hoặc thi đấu tại VNG IRONMAN Việt Nam 2026, giữ sự tương đồng về biểu cảm, tạo dáng hoặc trang phục

2️⃣ Bước 2: Đăng tải bài viết ở chế độ công khai, chia sẻ về khoảnh khắc trong bức ảnh và cảm xúc khi sẵn sàng quay trở lại chinh phục VNG IRONMAN Việt Nam 2026, đính kèm hashtags #VNGIRONMANDaNang2026 #MyIRONMANJourney #LifeatVNG

3️⃣ Bước 3: Điền form xác nhận tại: https://bit.ly/MyIRONMANJourney

‼️ Lưu ý:
• Bài đăng/Trang cá nhân phải ở chế độ công khai để BTC xác nhận tham gia.
• Kết quả sẽ được công bố tại phần bình luận của bài viết này vào ngày 15/05/2026. Thông tin nhận quà sẽ được gửi qua email cá nhân của người chiến thắng.

Hãy cùng Life at VNG nhìn lại “day one” của bạn và sẵn sàng cho “one day” - cột mốc chinh phục phiên bản mạnh mẽ hơn của chính mình trong mùa giải IRONMAN sắp tới nhé! 😎

#LifeatVNG #VNGIRONMANDaNang2026 #IMVietnam #EmbracingChallenges #EmbracingEveryIMpossible #MyIRONMANJourney
""".strip()


PROJECT = {
    "brand_name": "GreenNode",
    "brand_exclusions": ["GreenNode", "VNGCampus", "AIAgent"],
    "tone": "casual",
    "forbidden_words": [],
    "preferred_terms": {},
    "is_social_media": True,
}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    image_path = Path(IMAGE_PATH)
    if not IMAGE_PATH or not image_path.exists():
        print("Please set IMAGE_PATH to an existing image file.")
        return 1
    if not CAPTION or CAPTION == "Paste your caption here.":
        print("Please paste caption text into CAPTION.")
        return 1

    content_type = mimetypes.guess_type(str(image_path))[0] or "application/octet-stream"
    url = f"{BASE_URL.rstrip('/')}/check/image"
    data = {
        "caption": CAPTION,
        "project_json": json.dumps(PROJECT, ensure_ascii=False),
        "enable_llm": "true",
    }

    with image_path.open("rb") as image_file:
        files = {
            "images": (image_path.name, image_file, content_type),
        }
        response = requests.post(url, data=data, files=files, timeout=180)

    print(f"POST {url}")
    print(f"HTTP {response.status_code}")
    print()

    try:
        result = response.json()
    except ValueError:
        print(response.text)
        return 1

    print(json.dumps(result, ensure_ascii=False, indent=2))

    output_path = Path(__file__).with_name("last_image_check_response.json")
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(f"Saved full response to: {output_path}")

    return 0 if response.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
