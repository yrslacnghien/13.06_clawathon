"""Content Quality Checker Agent.

FastAPI orchestrator that:
1. Loads the content-quality-checker skill at startup.
2. Exposes POST /check — runs the full pipeline:
   - Deterministic checks (regex)
   - Gemma 4 quick pass (typos, diacritics)
   - Minimax 2.5 deep pass (homophones, context, image OCR)
3. Returns scored JSON with issues + corrected_text.
"""

import asyncio
import base64
import json
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from skill_loader import SkillLoader
from checkers.deterministic import (
    check_spacing,
    check_punctuation,
    check_capitalization_basic,
    check_forbidden_words,
)
from checkers.gemma_checker import GemmaChecker
from checkers.minimax_checker import MinimaxChecker
from scorer import (
    compute_score,
    build_corrected_text,
    deduplicate_issues,
    sort_issues_for_display,
)


load_dotenv()

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
log = logging.getLogger("agent")


# ---- Configuration ----------------------------------------------------------


def env_value(name: str, default: str = "") -> str:
    """Read an env var, treating missing or blank values as the default."""
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    return value.strip()


SKILL_PATH = Path(os.environ.get(
    "SKILL_PATH",
    str(Path(__file__).parent.parent / "content-quality-checker"),
))

AI_PLATFORM_ENDPOINT = env_value(
    "AI_PLATFORM_ENDPOINT",
    "https://maas-llm-aiplatform-hcm.api.vngcloud.vn/v1/chat/completions",
)
AI_PLATFORM_API_KEY = env_value("AI_PLATFORM_API_KEY")
AI_PLATFORM_MODEL = env_value("AI_PLATFORM_MODEL", "minimax/minimax-m2.5")
AI_PLATFORM_VISION_MODEL = env_value("AI_PLATFORM_VISION_MODEL")

GEMMA_ENDPOINT = env_value(
    "GEMMA_ENDPOINT",
    "https://api.example-gemma.ai/v1/chat/completions",
)
GEMMA_API_KEY = env_value("GEMMA_API_KEY")
GEMMA_MODEL = env_value("GEMMA_MODEL", "gemma-4")

ENABLE_LLM = env_value("ENABLE_LLM", "true").lower() == "true"
LLM_MAX_TOKENS = int(env_value("LLM_MAX_TOKENS", "2000"))
LLM_TOP_P = float(env_value("LLM_TOP_P", "0.95"))
LLM_PRESENCE_PENALTY = float(env_value("LLM_PRESENCE_PENALTY", "0"))
LLM_INSTRUCTION_ROLE = env_value("LLM_INSTRUCTION_ROLE", "assistant")
LLM_FORCE_JSON = env_value("LLM_FORCE_JSON", "false").lower() == "true"
MAX_IMAGE_BYTES = int(env_value("MAX_IMAGE_BYTES", str(8 * 1024 * 1024)))

LLM_CLIENT_KWARGS = {
    "max_tokens": LLM_MAX_TOKENS,
    "top_p": LLM_TOP_P,
    "presence_penalty": LLM_PRESENCE_PENALTY,
    "instruction_role": LLM_INSTRUCTION_ROLE,
    "force_json": LLM_FORCE_JSON,
}


# ---- Singletons (loaded at startup) -----------------------------------------

class AgentState:
    skill: Optional[SkillLoader] = None
    gemma: Optional[GemmaChecker] = None
    minimax: Optional[MinimaxChecker] = None


state = AgentState()


def build_skill_context(skill: SkillLoader) -> dict[str, str]:
    context = dict(skill.refs)
    context["skill-md"] = skill.skill_md
    return context


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Loading skill from %s", SKILL_PATH)
    state.skill = SkillLoader(SKILL_PATH)
    log.info("Skill loaded. Categories: %s", state.skill.list_categories())
    skill_context = build_skill_context(state.skill)

    if ENABLE_LLM:
        if GEMMA_API_KEY:
            state.gemma = GemmaChecker(
                GEMMA_ENDPOINT,
                GEMMA_API_KEY,
                GEMMA_MODEL,
                skill_context=skill_context,
                **LLM_CLIENT_KWARGS,
            )
            log.info("Gemma checker initialized (model=%s)", GEMMA_MODEL)
        else:
            log.warning("GEMMA_API_KEY not set — Gemma checks disabled")

        if AI_PLATFORM_API_KEY:
            state.minimax = MinimaxChecker(
                AI_PLATFORM_ENDPOINT,
                AI_PLATFORM_API_KEY,
                AI_PLATFORM_MODEL,
                vision_model=AI_PLATFORM_VISION_MODEL,
                skill_context=skill_context,
                **LLM_CLIENT_KWARGS,
            )
            log.info(
                "AI Platform checker initialized (model=%s, vision_model=%s)",
                AI_PLATFORM_MODEL,
                AI_PLATFORM_VISION_MODEL or "<not configured>",
            )
        else:
            log.warning("AI_PLATFORM_API_KEY not set — AI Platform checks disabled")
    else:
        log.info("ENABLE_LLM=false — running deterministic checks only")

    yield
    log.info("Shutting down")


# ---- Schema -----------------------------------------------------------------

class ProjectInfo(BaseModel):
    """Project-level context that customizes the check."""
    brand_name: str = ""
    brand_exclusions: list[str] = Field(
        default_factory=list,
        description="Brand names that should NOT be flagged as SP-08 CamelCase errors",
    )
    tone: str = Field("casual", description="formal | casual | playful")
    forbidden_words: list[str] = Field(default_factory=list)
    preferred_terms: dict[str, str] = Field(
        default_factory=dict,
        description="Map of preferred terms: { 'users': 'customers' }",
    )
    is_social_media: bool = True


class CheckRequest(BaseModel):
    text: str = Field(..., description="The post body to check")
    images: list[str] = Field(
        default_factory=list,
        description="Optional list of base64-encoded images (without data URI prefix)",
    )
    project: ProjectInfo = Field(default_factory=ProjectInfo)
    enable_llm: bool = Field(True, description="Set to false for fast deterministic-only check")


class IssueResponse(BaseModel):
    rule_id: str
    severity: str
    category: str
    position: str
    position_index: int
    found: str
    suggestion: str
    message: str
    confidence: Optional[str] = None
    source: Optional[str] = None


# ---- App --------------------------------------------------------------------

app = FastAPI(
    title="Content Quality Checker Agent",
    version="1.0.0",
    description="Proofreads and scores social media posts using a Claude skill + LLMs.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "name": "Content Quality Checker Agent",
        "version": "1.0.0",
        "skill_loaded": state.skill is not None,
        "gemma_enabled": state.gemma is not None,
        "minimax_enabled": state.minimax is not None,
        "endpoints": ["/check", "/check/image", "/health", "/health/model", "/skill/info"],
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "skill_loaded": state.skill is not None,
        "llm_ready": state.minimax is not None or state.gemma is not None,
    }


@app.get("/health/model")
async def model_health():
    checker = state.minimax or state.gemma
    if not checker:
        return {
            "status": "disabled",
            "message": "No AI model checker is configured. Set AI_PLATFORM_API_KEY or GEMMA_API_KEY.",
            "minimax_enabled": state.minimax is not None,
            "gemma_enabled": state.gemma is not None,
        }

    client = checker.client
    started = perf_counter()
    try:
        content = await client.chat(
            system="You are an AI model health check. Reply with OK only.",
            user="Health check",
            force_json=False,
            temperature=0,
            max_tokens=16,
        )

        elapsed_ms = round((perf_counter() - started) * 1000)
        return {
            "status": "ok",
            "model": client.model,
            "endpoint": client.endpoint,
            "latency_ms": elapsed_ms,
            "response_preview": str(content)[:120],
        }
    except Exception as e:
        elapsed_ms = round((perf_counter() - started) * 1000)
        log.exception("AI model health check failed")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "error",
                "model": client.model,
                "endpoint": client.endpoint,
                "latency_ms": elapsed_ms,
                "error_type": type(e).__name__,
                "error": str(e),
            },
        ) from e


@app.get("/skill/info")
async def skill_info():
    if not state.skill:
        raise HTTPException(503, "Skill not loaded")
    return {
        "skill_path": str(state.skill.skill_path),
        "categories": state.skill.list_categories(),
    }


async def run_content_check(req: CheckRequest) -> dict:
    if not state.skill:
        raise HTTPException(503, "Skill not loaded")

    if not req.text or not req.text.strip():
        return {
            "score": None,
            "grade": None,
            "issues": [{
                "rule_id": "EMPTY_INPUT",
                "severity": "critical",
                "category": "input",
                "message": "No text provided",
                "found": "",
                "suggestion": "",
                "position": "n/a",
                "position_index": -1,
            }],
            "original_text": req.text,
            "corrected_text": req.text,
        }

    text = req.text
    project = req.project
    use_llm = req.enable_llm and ENABLE_LLM

    log.info("Checking text (len=%d, images=%d, llm=%s)",
             len(text), len(req.images), use_llm)

    all_issues: list[dict] = []

    # ---- Phase 1: Deterministic (always) ----
    exclusions = set(project.brand_exclusions)
    if project.brand_name:
        exclusions.add(project.brand_name)

    all_issues.extend(check_spacing(text, exclusions))
    all_issues.extend(check_punctuation(text))
    all_issues.extend(check_capitalization_basic(
        text,
        brand_names=[project.brand_name] if project.brand_name else None,
    ))
    all_issues.extend(check_forbidden_words(text, project.forbidden_words))

    deterministic_count = len(all_issues)
    log.info("Deterministic checks found %d issues", deterministic_count)

    # ---- Phase 2 & 3: LLM checks (parallel) ----
    image_checks: list[dict] = []
    if use_llm:
        llm_tasks = []

        if state.gemma:
            llm_tasks.append(("issues", None, state.gemma.check_basic_typos(text)))

        if state.minimax:
            llm_tasks.append(("issues", None, state.minimax.check_vietnamese_tone(text)))
            llm_tasks.append(("issues", None, state.minimax.check_homophone_and_context(text)))

            for image_index, img_b64 in enumerate(req.images):
                llm_tasks.append((
                    "image_check",
                    image_index,
                    state.minimax.check_image_vs_text_report(text, img_b64),
                ))

        if llm_tasks:
            results = await asyncio.gather(
                *(task for _, _, task in llm_tasks),
                return_exceptions=True,
            )
            for (kind, image_index, _), r in zip(llm_tasks, results):
                if isinstance(r, Exception):
                    log.error("LLM task failed: %s", r)
                    if kind == "image_check":
                        image_checks.append({
                            "image_index": image_index,
                            "status": "error",
                            "error": str(r),
                            "image_text_extracted": "",
                            "conflicts_count": 0,
                        })
                    continue
                if kind == "image_check" and isinstance(r, dict):
                    report = {
                        "image_index": image_index,
                        "status": r.get("status", "unknown"),
                        "model": r.get("model", ""),
                        "image_text_extracted": r.get("image_text_extracted", ""),
                        "conflicts_count": r.get("conflicts_count", 0),
                    }
                    if r.get("error"):
                        report["error"] = r["error"]
                    if isinstance(r.get("raw"), dict):
                        report["raw"] = r["raw"]
                    image_checks.append(report)
                    all_issues.extend(r.get("issues", []))
                elif isinstance(r, list):
                    all_issues.extend(r)

        log.info("After LLM checks: %d total issues (+%d from LLM)",
                 len(all_issues), len(all_issues) - deterministic_count)

    # ---- Phase 4: Deduplicate + sort + score ----
    all_issues = deduplicate_issues(all_issues)
    all_issues = sort_issues_for_display(all_issues)

    score_result = compute_score(all_issues)
    corrected = build_corrected_text(text, all_issues)

    # ---- Build response ----
    response = {
        "score": score_result["score"],
        "grade": score_result["grade"],
        "total_issues": score_result["total_issues"],
        "issues_by_severity": score_result["issues_by_severity"],
        "categories": score_result["categories"],
        "issues": all_issues,
        "original_text": text,
        "corrected_text": corrected,
        "metadata": {
            "deterministic_checks": deterministic_count,
            "llm_used": use_llm and (state.gemma is not None or state.minimax is not None),
            "images_checked": len(req.images),
            "image_checks": image_checks,
        },
    }
    return response


def parse_project_json(project_json: str) -> ProjectInfo:
    if not project_json or not project_json.strip():
        return ProjectInfo()
    try:
        raw = json.loads(project_json)
    except json.JSONDecodeError as e:
        raise HTTPException(400, f"Invalid project_json: {e}") from e
    try:
        return ProjectInfo.model_validate(raw)
    except Exception as e:
        raise HTTPException(400, f"Invalid project_json shape: {e}") from e


async def image_to_data_uri(upload: UploadFile) -> tuple[str, dict]:
    content_type = upload.content_type or "application/octet-stream"
    if not content_type.startswith("image/"):
        raise HTTPException(
            400,
            f"File '{upload.filename}' must be an image, got '{content_type}'",
        )

    data = await upload.read()
    if not data:
        raise HTTPException(400, f"File '{upload.filename}' is empty")
    if len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(
            413,
            f"File '{upload.filename}' is too large. Max size is {MAX_IMAGE_BYTES} bytes",
        )

    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{content_type};base64,{encoded}", {
        "filename": upload.filename,
        "content_type": content_type,
        "size_bytes": len(data),
    }


@app.post("/check/image")
async def check_image_content(
    caption: str = Form(..., description="Caption or post text to compare with image text"),
    images: list[UploadFile] = File(..., description="One or more image files"),
    project_json: str = Form("{}", description="Optional ProjectInfo JSON object"),
    enable_llm: bool = Form(True),
):
    if not state.skill:
        raise HTTPException(503, "Skill not loaded")
    if not caption or not caption.strip():
        raise HTTPException(400, "caption is required")
    if not images:
        raise HTTPException(400, "At least one image is required")
    if enable_llm and ENABLE_LLM and not state.minimax:
        raise HTTPException(
            503,
            "Image consistency checks require AI_PLATFORM_API_KEY and ENABLE_LLM=true",
        )

    encoded_images: list[str] = []
    image_metadata: list[dict] = []
    for upload in images:
        encoded, metadata = await image_to_data_uri(upload)
        encoded_images.append(encoded)
        image_metadata.append(metadata)

    req = CheckRequest(
        text=caption,
        images=encoded_images,
        project=parse_project_json(project_json),
        enable_llm=enable_llm,
    )
    response = await run_content_check(req)
    response["metadata"]["input_mode"] = "multipart_image_caption"
    response["metadata"]["uploaded_images"] = image_metadata

    failed_image_checks = [
        check for check in response["metadata"].get("image_checks", [])
        if check.get("status") != "ok"
    ]
    if failed_image_checks:
        raise HTTPException(
            503,
            {
                "status": "error",
                "message": "One or more image consistency checks did not complete",
                "image_checks": failed_image_checks,
                "response": response,
            },
        )

    return response


@app.post("/check")
async def check_content(req: CheckRequest):
    return await run_content_check(req)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "agent:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=False,
    )
