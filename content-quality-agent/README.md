# Content Quality Checker Agent

AI Agent dùng FastAPI để kiểm tra chất lượng bài đăng/caption mạng xã hội. Agent kết hợp:

- deterministic rules bằng Python regex, chạy nhanh và không tốn chi phí
- skill `content-quality-checker` làm source of truth cho rule/spec
- AI Platform text model để kiểm tra lỗi ngữ nghĩa, lỗi dấu tiếng Việt, typo theo ngữ cảnh
- AI Platform vision/multimodal model để OCR ảnh và so sánh ảnh với caption

## Cấu trúc thư mục

```text
13.06_clawathon/
├── content-quality-checker/        # Skill: SKILL.md + references + test cases
│   ├── SKILL.md
│   ├── references/
│   └── tests/
└── content-quality-agent/          # FastAPI agent
    ├── agent.py                    # API entrypoint
    ├── skill_loader.py             # Load skill/references
    ├── scorer.py                   # Tính score, grade, corrected_text
    ├── checkers/
    │   ├── deterministic.py        # Regex checks
    │   ├── gemma_checker.py        # Optional typo pass
    │   ├── minimax_checker.py      # Text + image checks qua AI Platform
    │   └── llm_base.py             # OpenAI-compatible client
    ├── prompts/                    # Prompt template cho từng tác vụ AI
    ├── tests/
    ├── Dockerfile
    ├── docker-compose.yml
    ├── requirements.txt
    └── .env.example
```

## Skill và prompt được dùng như thế nào

Khi app khởi động, agent load toàn bộ `content-quality-checker/SKILL.md` và các file trong `content-quality-checker/references/`.

Khi gọi AI model, agent ghép:

```text
prompts/*.txt + authoritative rules từ content-quality-checker/references/*.md
```

Mapping hiện tại:

- `basic_typo.txt` + `typo-rules.md` + `brand-style-rules.md` + `output-format.md`
- `vietnamese_tone.txt` + `vietnamese-tone-rules.md` + `output-format.md`
- `homophone_context.txt` + `typo-rules.md` + `brand-style-rules.md` + `output-format.md`
- `image_check.txt` + `SKILL.md` + `output-format.md`

Nói ngắn gọn: `prompts/` là template nhiệm vụ cụ thể, còn `content-quality-checker/` là rule/spec gốc được inject vào prompt runtime.

## Luồng xử lý

```text
POST /check hoặc POST /check/image
→ validate input
→ deterministic checks: spacing, punctuation, capitalization, forbidden words
→ nếu enable_llm=true:
   → Gemma optional: typo cơ bản
   → AI Platform text model: dấu tiếng Việt, homophone, semantic/context
   → AI Platform vision model: OCR ảnh và so sánh với caption
→ deduplicate issues
→ tính score/grade
→ build corrected_text
→ trả JSON response
```

## Yêu cầu trước khi chạy

- Docker Desktop nếu chạy bằng Docker Compose
- Python 3.11+ nếu chạy trực tiếp local
- API key của VNGCloud AI Platform nếu muốn bật LLM
- Một model text, ví dụ `minimax/minimax-m2.5`
- Một model vision/multimodal nếu muốn dùng `/check/image`

Lưu ý: `minimax/minimax-m2.5` là text-only, không dùng được cho ảnh. Với `/check/image`, cần set `AI_PLATFORM_VISION_MODEL` thành model hỗ trợ image input trên AI Platform.

## Cấu hình `.env`

Tạo file `.env` từ template:

```bash
cd content-quality-agent
cp .env.example .env
```

Ví dụ cấu hình tối thiểu để chạy deterministic-only:

```env
ENABLE_LLM=false
PORT=8000
```

Ví dụ cấu hình để gọi AI text model:

```env
ENABLE_LLM=true
AI_PLATFORM_API_KEY=your_key_here
AI_PLATFORM_ENDPOINT=https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1/chat/completions
AI_PLATFORM_MODEL=minimax/minimax-m2.5
```

Ví dụ cấu hình thêm image/caption consistency:

```env
AI_PLATFORM_VISION_MODEL=your_multimodal_model_name
```

## Chạy bằng Docker Compose

Chạy từ thư mục `content-quality-agent`:

```bash
cd content-quality-agent
docker compose up --build
```

Chạy nền:

```bash
docker compose up -d --build
```

Dừng container:

```bash
docker compose down
```

Docker Compose dùng build context là thư mục cha (`..`) để image include cả:

- `content-quality-agent/`
- `content-quality-checker/`

Vì vậy nếu sửa skill/rules thì cần rebuild image.

## Chạy bằng Docker thủ công

Chạy từ root repo `13.06_clawathon`:

```bash
docker build -f content-quality-agent/Dockerfile -t content-quality-agent:latest .
```

Deterministic-only:

```bash
docker run --rm -p 8000:8000 \
  -e ENABLE_LLM=false \
  --name content-quality-agent \
  content-quality-agent:latest
```

Có AI text model:

```bash
docker run --rm -p 8000:8000 \
  -e ENABLE_LLM=true \
  -e AI_PLATFORM_API_KEY=your_key_here \
  -e AI_PLATFORM_MODEL=minimax/minimax-m2.5 \
  --name content-quality-agent \
  content-quality-agent:latest
```

## Chạy trực tiếp bằng Python

```bash
cd content-quality-agent
pip install -r requirements.txt
python agent.py
```

Hoặc:

```bash
uvicorn agent:app --reload --port 8000
```

## API endpoints

### `GET /health`

Kiểm tra app và skill đã load chưa:

```bash
curl http://localhost:8000/health
```

Response ví dụ:

```json
{
  "status": "ok",
  "skill_loaded": true,
  "llm_ready": true
}
```

### `GET /health/model`

Gọi thử AI text model bằng prompt rất nhỏ:

```bash
curl http://localhost:8000/health/model
```

Nếu key/model đúng, response có `status=ok`, `model`, `endpoint`, `latency_ms`.

### `GET /skill/info`

Xem skill path và danh sách reference files đã load:

```bash
curl http://localhost:8000/skill/info
```

### `POST /check`

Kiểm tra một đoạn text/caption.

Git Bash:

```bash
curl -X POST http://localhost:8000/check \
  -H "Content-Type: application/json" \
  -d '{"text":"GreenNodeClaw-a-thon da mo man  bang buoi dao tao!!","project":{"brand_name":"GreenNode","brand_exclusions":["GreenNode"]},"enable_llm":false}'
```

PowerShell:

```powershell
$body = @{
  text = "GreenNodeClaw-a-thon đã mở màn  bằng buổi đào tạo!!"
  project = @{
    brand_name = "GreenNode"
    brand_exclusions = @("GreenNode")
  }
  enable_llm = $false
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Uri http://localhost:8000/check -Method Post -ContentType "application/json; charset=utf-8" -Body $body
```

### `POST /check/image`

Upload ảnh và caption để kiểm tra sự đồng nhất giữa nội dung ảnh và caption.

```bash
curl -X POST http://localhost:8000/check/image \
  -F 'caption=Sale 50% đến ngày 30/6 cho GreenNode Claw-a-thon' \
  -F 'images=@/path/to/image.png' \
  -F 'project_json={"brand_name":"GreenNode","brand_exclusions":["GreenNode","VNGCampus","AIAgent"]}' \
  -F 'enable_llm=true'
```

Endpoint này yêu cầu:

- `ENABLE_LLM=true`
- `AI_PLATFORM_API_KEY` có giá trị
- `AI_PLATFORM_VISION_MODEL` là model multimodal hỗ trợ image input

Nếu image check không chạy được, endpoint trả HTTP `503` để tránh hiểu nhầm là đã check ảnh thành công.

## Response chính

Response `/check` và `/check/image` có dạng:

```json
{
  "score": 88,
  "grade": "B",
  "total_issues": 3,
  "issues_by_severity": {
    "critical": 0,
    "major": 2,
    "minor": 1,
    "suggestion": 0
  },
  "categories": {},
  "issues": [],
  "original_text": "...",
  "corrected_text": "...",
  "metadata": {
    "deterministic_checks": 3,
    "llm_used": false,
    "images_checked": 0,
    "image_checks": []
  }
}
```

Với `/check/image`, `metadata.image_checks` sẽ có OCR/check report:

```json
{
  "image_index": 0,
  "status": "ok",
  "model": "your_multimodal_model_name",
  "image_text_extracted": "...",
  "conflicts_count": 0,
  "raw": {}
}
```

## Test

Unit test deterministic:

```bash
PYTHONUTF8=1 python content-quality-agent/tests/test_deterministic.py
```

Integration test API:

```bash
PYTHONUTF8=1 python content-quality-agent/tests/test_api.py http://localhost:8000
```

Manual text test:

```bash
PYTHONUTF8=1 python content-quality-agent/tests/check_content_manual.py http://localhost:8000 --llm
```

Manual image test:

```bash
PYTHONUTF8=1 python content-quality-agent/tests/check_image_manual.py http://localhost:8000
```

File output của manual tests:

- `content-quality-agent/tests/last_check_response.json`
- `content-quality-agent/tests/last_image_check_response.json`

## Troubleshooting

### `/health` có `llm_ready=false`

Kiểm tra `.env`:

```env
ENABLE_LLM=true
AI_PLATFORM_API_KEY=your_key_here
```

Sau đó rebuild container.

### `/check/image` báo model không multimodal

Lỗi ví dụ:

```text
minimax-m2.5 is not a multimodal model
```

Cách xử lý: giữ `AI_PLATFORM_MODEL=minimax/minimax-m2.5` cho text, và set thêm:

```env
AI_PLATFORM_VISION_MODEL=your_multimodal_model_name
```

### Git Bash gửi tiếng Việt bị lỗi parse body

Dùng JSON file hoặc PowerShell. Với Git Bash:

```bash
cat > payload.json <<'EOF'
{"text":"GreenNodeClaw-a-thon đã mở màn  bằng buổi đào tạo!!","enable_llm":false}
EOF

curl -X POST http://localhost:8000/check \
  -H "Content-Type: application/json; charset=utf-8" \
  --data-binary @payload.json
```
