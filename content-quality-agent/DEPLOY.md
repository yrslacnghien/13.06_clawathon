# Hướng Dẫn Build, Chạy Local Và Deploy

Tài liệu này hướng dẫn cách chạy agent ở local bằng Docker/Python và chuẩn bị deploy lên GreenNode AgentBase.

## 1. Chuẩn bị

Repo cần giữ cấu trúc 2 thư mục song song:

```text
13.06_clawathon/
├── content-quality-checker/   # Skill/rules
└── content-quality-agent/     # FastAPI agent
```

Dockerfile của agent copy cả 2 thư mục vào image, nên build context phải là root repo `13.06_clawathon`, không phải chỉ folder `content-quality-agent`.

## 2. Cấu hình `.env`

Tạo `.env`:

```bash
cd content-quality-agent
cp .env.example .env
```

Chạy không gọi AI:

```env
ENABLE_LLM=false
PORT=8000
```

Chạy có AI text model:

```env
ENABLE_LLM=true
AI_PLATFORM_API_KEY=your_key_here
AI_PLATFORM_ENDPOINT=https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1/chat/completions
AI_PLATFORM_MODEL=minimax/minimax-m2.5
```

Chạy thêm endpoint ảnh `/check/image`:

```env
AI_PLATFORM_VISION_MODEL=your_multimodal_model_name
```

Lưu ý: `minimax/minimax-m2.5` là text-only. Không dùng model này cho ảnh.

## 3. Chạy bằng Docker Compose

Từ folder `content-quality-agent`:

```bash
docker compose up --build
```

Chạy nền:

```bash
docker compose up -d --build
```

Xem logs:

```bash
docker compose logs -f
```

Dừng:

```bash
docker compose down
```

## 4. Build Docker thủ công

Từ root repo `13.06_clawathon`:

```bash
docker build -f content-quality-agent/Dockerfile -t content-quality-agent:latest .
```

Chạy deterministic-only:

```bash
docker run --rm -p 8000:8000 \
  -e ENABLE_LLM=false \
  --name content-quality-agent \
  content-quality-agent:latest
```

Chạy có AI text model:

```bash
docker run --rm -p 8000:8000 \
  -e ENABLE_LLM=true \
  -e AI_PLATFORM_API_KEY=your_key_here \
  -e AI_PLATFORM_MODEL=minimax/minimax-m2.5 \
  --name content-quality-agent \
  content-quality-agent:latest
```

Chạy có thêm vision model:

```bash
docker run --rm -p 8000:8000 \
  -e ENABLE_LLM=true \
  -e AI_PLATFORM_API_KEY=your_key_here \
  -e AI_PLATFORM_MODEL=minimax/minimax-m2.5 \
  -e AI_PLATFORM_VISION_MODEL=your_multimodal_model_name \
  --name content-quality-agent \
  content-quality-agent:latest
```

## 5. Smoke test local

Health:

```bash
curl http://localhost:8000/health
```

Model health:

```bash
curl http://localhost:8000/health/model
```

Skill info:

```bash
curl http://localhost:8000/skill/info
```

Text check không gọi AI:

```bash
curl -X POST http://localhost:8000/check \
  -H "Content-Type: application/json" \
  -d '{"text":"GreenNodeClaw-a-thon da mo man  bang buoi dao tao!!","project":{"brand_name":"GreenNode","brand_exclusions":["GreenNode"]},"enable_llm":false}'
```

Image + caption check:

```bash
curl -X POST http://localhost:8000/check/image \
  -F 'caption=Sale 50% đến ngày 30/6 cho GreenNode Claw-a-thon' \
  -F 'images=@/path/to/image.png' \
  -F 'project_json={"brand_name":"GreenNode","brand_exclusions":["GreenNode","VNGCampus","AIAgent"]}' \
  -F 'enable_llm=true'
```

## 6. Chạy test scripts

Deterministic tests:

```bash
PYTHONUTF8=1 python content-quality-agent/tests/test_deterministic.py
```

API integration tests:

```bash
PYTHONUTF8=1 python content-quality-agent/tests/test_api.py http://localhost:8000
```

Manual text check:

```bash
PYTHONUTF8=1 python content-quality-agent/tests/check_content_manual.py http://localhost:8000 --llm
```

Manual image check:

```bash
PYTHONUTF8=1 python content-quality-agent/tests/check_image_manual.py http://localhost:8000
```

## 7. Deploy lên GreenNode AgentBase

Flow đề xuất:

1. Đăng nhập AgentBase portal.
2. Lấy `Client ID`, `Client Secret`, `API Key` nếu portal yêu cầu.
3. Tạo GitHub repo chứa project.
4. Đảm bảo repo có cả:
   - `content-quality-agent/`
   - `content-quality-checker/`
5. Build agent bằng Dockerfile:
   - Dockerfile path: `content-quality-agent/Dockerfile`
   - build context: root repo
6. Cấu hình environment variables:
   - `ENABLE_LLM=true`
   - `AI_PLATFORM_API_KEY`
   - `AI_PLATFORM_ENDPOINT`
   - `AI_PLATFORM_MODEL`
   - `AI_PLATFORM_VISION_MODEL` nếu dùng `/check/image`
   - optional: `GEMMA_API_KEY`, `GEMMA_ENDPOINT`, `GEMMA_MODEL`
7. Deploy và chờ service active.
8. Verify bằng `/health`, `/health/model`, `/skill/info`, `/check`.

## 8. Verify deployment

```bash
AGENT_URL=https://your-agent-url

curl $AGENT_URL/health
curl $AGENT_URL/health/model
curl $AGENT_URL/skill/info
```

Text check:

```bash
curl -X POST $AGENT_URL/check \
  -H "Content-Type: application/json" \
  -d '{"text":"GreenNodeClaw-a-thon da mo man  bang buoi dao tao!!","project":{"brand_name":"GreenNode","brand_exclusions":["GreenNode"]},"enable_llm":false}'
```

Kỳ vọng:

- `score < 100`
- có issue `SP-08`
- có issue `PU-02` nếu text có `!!`

## 9. Monitoring

Endpoints nên monitor:

- `GET /health`: liveness, skill load status
- `GET /health/model`: AI Platform text model status
- `GET /skill/info`: xác nhận skill path và references đã load
- `POST /check`: text check
- `POST /check/image`: image/caption consistency check

Alert gợi ý:

- `/health` không trả `status=ok`
- `/health/model` trả HTTP 503
- `/check` p95 latency > 20s
- `/check/image` trả HTTP 503 do vision model chưa cấu hình hoặc provider lỗi

## 10. Cập nhật skill/rules

Skill được bake vào Docker image tại build time:

```dockerfile
COPY content-quality-checker/ /app/content-quality-checker/
```

Nếu sửa file trong `content-quality-checker/`, cần rebuild image:

```bash
cd content-quality-agent
docker compose up -d --build
```

Trong dev có thể mount volume skill để khỏi rebuild, nhưng khi deploy AgentBase nên bake skill vào image để version rõ ràng.

## 11. Troubleshooting nhanh

### Docker build báo không tìm thấy `content-quality-checker`

Bạn đang build sai context. Chạy từ root repo:

```bash
docker build -f content-quality-agent/Dockerfile -t content-quality-agent:latest .
```

### `/health` có `llm_ready=false`

Kiểm tra:

```env
ENABLE_LLM=true
AI_PLATFORM_API_KEY=your_key_here
```

Sau đó rebuild/restart container.

### `/check/image` báo image check disabled

Thiếu vision model:

```env
AI_PLATFORM_VISION_MODEL=your_multimodal_model_name
```

### `/check/image` báo model không multimodal

Đổi `AI_PLATFORM_VISION_MODEL` sang model có support image input. Không dùng `minimax/minimax-m2.5` cho ảnh.
