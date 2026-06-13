# Content Quality Checker Agent

AI Agent kiểm tra chất lượng nội dung social media post — phát hiện lỗi chính tả, dấu câu, khoảng trắng, dấu tiếng Việt, và cross-check text trên ảnh.

## Cấu trúc

| Folder | Mô tả |
|--------|-------|
| `content-quality-checker/` | Bộ skill (40 rules, 7 categories) |
| `content-quality-agent/` | FastAPI agent + Dockerfile |
| `greennode-agentbase-skills/` | GreenNode AgentBase deployment skills |

## Pipeline## Quick Start

```bash
cd content-quality-agent
cp .env.example .env   # fill API keys
pip install -r requirements.txt
python agent.py         # starts on :8000
```

## Docker

```bash
docker build -f content-quality-agent/Dockerfile -t cqa:latest .
docker run -p 8000:8000 -e MINIMAX_API_KEY=sk-xxx cqa:latest
```

## Test

```bash
curl -X POST http://localhost:8000/check \
  -H 'Content-Type: application/json' \
  -d '{"text": "GreenNodeClaw-a-thon!!", "enable_llm": false}'
```

Built for GreenNode Claw-a-thon 2026.
