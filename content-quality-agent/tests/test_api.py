"""Integration tests for the agent's HTTP API.

Run a smoke test against the running server:
    python tests/test_api.py [base_url]

Default base_url is http://localhost:8000
"""

import sys
import requests


def test_health(base_url: str) -> None:
    r = requests.get(f"{base_url}/health", timeout=5)
    r.raise_for_status()
    data = r.json()
    assert data["status"] == "ok"
    assert data["skill_loaded"] is True
    print("  ✓  /health")


def test_model_health(base_url: str) -> None:
    r = requests.get(f"{base_url}/health/model", timeout=30)
    if r.status_code == 503:
        data = r.json()
        detail = data.get("detail", {})
        assert detail.get("status") == "error"
        print(f"  ✗  /health/model — {detail.get('model')} error: {detail.get('error')}")
        raise AssertionError(f"AI model health check failed: {detail}")

    r.raise_for_status()
    data = r.json()
    assert data["status"] in {"ok", "disabled"}
    if data["status"] == "ok":
        assert "model" in data
        assert "latency_ms" in data
        print(f"  ✓  /health/model — model={data['model']}, latency={data['latency_ms']}ms")
    else:
        print("  ✓  /health/model — disabled")


def test_skill_info(base_url: str) -> None:
    r = requests.get(f"{base_url}/skill/info", timeout=5)
    r.raise_for_status()
    data = r.json()
    assert "categories" in data
    assert "spacing-rules" in data["categories"]
    print("  ✓  /skill/info")


def test_check_deterministic_only(base_url: str) -> None:
    payload = {
        "text": "GreenNodeClaw-a-thon đã mở màn  bằng buổi đào tạo!!",
        "project": {
            "brand_name": "GreenNode",
            "brand_exclusions": ["GreenNode"],
        },
        "enable_llm": False,
    }
    r = requests.post(f"{base_url}/check", json=payload, timeout=10)
    r.raise_for_status()
    data = r.json()
    assert isinstance(data["score"], int)
    assert data["score"] < 100  # has issues
    assert data["total_issues"] >= 3

    # Must detect SP-08 on GreenNodeClaw-a-thon
    rule_ids = {i["rule_id"] for i in data["issues"]}
    assert "SP-08" in rule_ids, f"Expected SP-08, got: {rule_ids}"
    assert "PU-02" in rule_ids, f"Expected PU-02, got: {rule_ids}"
    print(f"  ✓  /check deterministic — score={data['score']}, issues={data['total_issues']}")


def test_check_empty_text(base_url: str) -> None:
    payload = {"text": "", "enable_llm": False}
    r = requests.post(f"{base_url}/check", json=payload, timeout=5)
    r.raise_for_status()
    data = r.json()
    assert any(i["rule_id"] == "EMPTY_INPUT" for i in data["issues"])
    print("  ✓  /check empty input")


def test_check_clean_text(base_url: str) -> None:
    payload = {
        "text": "Chào mừng bạn đến với cửa hàng của chúng tôi. Liên hệ để được tư vấn.",
        "enable_llm": False,
    }
    r = requests.post(f"{base_url}/check", json=payload, timeout=5)
    r.raise_for_status()
    data = r.json()
    assert data["score"] >= 90, f"Clean text should score high, got {data['score']}"
    print(f"  ✓  /check clean text — score={data['score']}")


def test_check_clawathon_sample(base_url: str) -> None:
    text = """🔥GREENnode CLAW-A-THON OFFLINE trainning: HƠN 600 STARTERS BƯỚC VÀO ĐƯỜNG ĐUA AI HACKATHON SÔI NỔI!
Ngày 10/06 vừa qua, GreenNodeClaw-a-thon đã mở màn bằng buổi đào tạo trực tiếp diễn ra tại VNGCampus, bắt đầu cho hành trình 7 ngày hackathon thực chiến. Chặng đua đã trở nên vô cùng xôi nổi với sự góp mặt của hơn 600 Tech và Non-tech Starter, ấp ủ hơn 300 ý tưởng AI Agent. Những con số này không chỉ tạo nên một khởi đầu ấn tượng, mà còn thể hiện rõ nét tinh thần sẵn sàng học hỏi, không ngại "đón nhận thách thức" tại PNG.
Để chuẩn bị tốt nhất cho hành trình 7 ngày hackathon, chương trình đã trang bị toàn diện cho các đội thi  từ tài nguyên đến kiến thức công nghệ:
⭐️Hành trang thực chiến từ A-Z: Chi tiết quy trình xây dựng một AI Agent hoàn chỉnh, đồng thời cung cấp cho staff các công cụ hỗ trợ về mặt kỹ thuật - bệ phóng quan trọng giúp hiện thực hóa các ý tưởng.
⭐️   Trải nghiệm DemoAI Agent: Các Starter cùng quan sát phần minh họa từ các bài toán thực tế, đồng thời “bắt tay” thực hành dưới sự hướng dẫn trực tiếp từ đội ngũ greenNode.
Bước vào giai đoạn xây dựng sản phẩm, chúc các đội thi luôn giữ vững sự tự, phát huy tối đa tinh thần sáng tạo để đưa các ý tưởng AIAgent về đích thành công. !
Life AT VNG sẽ tiếp tục cập nhật những diễn biến mới nhất của cuộc thi. Cùng theo dõi để không bỏ lỡ những màn bứt phá ấn tượng từ các đội thi nhé! 💪
#LifeatVNG #GreenNodeClawathon #GreenNode #AIAgent"""
    payload = {
        "text": text,
        "project": {
            "brand_name": "GreenNode",
            "brand_exclusions": ["GreenNode", "VNGCampus", "AIAgent"],
        },
        "enable_llm": False,
    }
    r = requests.post(f"{base_url}/check", json=payload, timeout=10)
    r.raise_for_status()
    data = r.json()
    assert isinstance(data["score"], int)
    assert data["score"] < 100
    assert data["total_issues"] >= 6

    rule_ids = {i["rule_id"] for i in data["issues"]}
    expected = {"SP-01", "SP-08", "SP-09", "PU-02", "CA-04", "CA-05"}
    missing = expected - rule_ids
    assert not missing, f"Expected {missing} in Claw-a-thon sample, got: {rule_ids}"
    print(f"  ✓  /check Claw-a-thon sample — score={data['score']}, issues={data['total_issues']}")


if __name__ == "__main__":
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    print(f"Testing against {base_url}")
    print()
    tests = [
        test_health,
        test_model_health,
        test_skill_info,
        test_check_deterministic_only,
        test_check_empty_text,
        test_check_clean_text,
        test_check_clawathon_sample,
    ]
    failed = 0
    for t in tests:
        try:
            t(base_url)
        except Exception as e:
            failed += 1
            print(f"  ✗  {t.__name__}: {type(e).__name__}: {e}")
    print()
    print(f"{len(tests) - failed}/{len(tests)} passed")
    sys.exit(1 if failed else 0)
