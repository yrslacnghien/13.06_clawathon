"""Manual content check script.

Paste your content into TEXT, then run:
    python content-quality-agent/tests/check_content_manual.py

Optional:
    python content-quality-agent/tests/check_content_manual.py http://localhost:8000 --llm
"""

import json
import sys
from pathlib import Path

import requests


BASE_URL = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "http://localhost:8000"
ENABLE_LLM = "--llm" in sys.argv


# Paste your post/content here.
TEXT = """🔥GREENnode CLAW-A-THON OFFLINE trainning: HƠN 600 STARTERS BƯỚC VÀO ĐƯỜNG ĐUA AI HACKATHON SÔI NỔI!
Ngày 10/06 vừa qua, GreenNodeClaw-a-thon đã mở màn bằng buổi đào tạo trực tiếp diễn ra tại VNGCampus, bắt đầu cho hành trình 7 ngày hackathon thực chiến. Chặng đua đã trở nên vô cùng xôi nổi với sự góp mặt của hơn 600 Tech và Non-tech Starter, ấp ủ hơn 300 ý tưởng AI Agent. Những con số này không chỉ tạo nên một khởi đầu ấn tượng, mà còn thể hiện rõ nét tinh thần sẵn sàng học hỏi, không ngại "đón nhận thách thức" tại PNG.
Để chuẩn bị tốt nhất cho hành trình 7 ngày hackathon, chương trình đã trang bị toàn diện cho các đội thi  từ tài nguyên đến kiến thức công nghệ:
⭐️Hành trang thực chiến từ A-Z: Chi tiết quy trình xây dựng một AI Agent hoàn chỉnh, đồng thời cung cấp cho staff các công cụ hỗ trợ về mặt kỹ thuật - bệ phóng quan trọng giúp hiện thực hóa các ý tưởng.
⭐️   Trải nghiệm DemoAI Agent: Các Starter cùng quan sát phần minh họa từ các bài toán thực tế, đồng thời “bắt tay” thực hành dưới sự hướng dẫn trực tiếp từ đội ngũ greenNode.
Bước vào giai đoạn xây dựng sản phẩm, chúc các đội thi luôn giữ vững sự tự, phát huy tối đa tinh thần sáng tạo để đưa các ý tưởng AIAgent về đích thành công. !
Life AT VNG sẽ tiếp tục cập nhật những diễn biến mới nhất của cuộc thi. Cùng theo dõi để không bỏ lỡ những màn bứt phá ấn tượng từ các đội thi nhé! 💪
#LifeatVNG #GreenNodeClawathon #GreenNode #AIAgent""".strip()


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

    if not TEXT or TEXT == "Paste your content here.":
        print("Please paste content into TEXT before running this script.")
        return 1

    payload = {
        "text": TEXT,
        "project": PROJECT,
        "enable_llm": ENABLE_LLM,
    }

    url = f"{BASE_URL.rstrip('/')}/check"
    response = requests.post(url, json=payload, timeout=120)

    print(f"POST {url}")
    print(f"HTTP {response.status_code}")
    print()

    try:
        data = response.json()
    except ValueError:
        print(response.text)
        return 1

    print(json.dumps(data, ensure_ascii=False, indent=2))

    output_path = Path(__file__).with_name("last_check_response.json")
    output_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print()
    print(f"Saved full response to: {output_path}")

    return 0 if response.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
