"""Minimax 2.5 checker — deep semantic + multimodal."""

import logging

from checkers.llm_base import (
    LLMClient,
    compose_prompt,
    load_prompt,
    extract_json,
    normalize_issue,
)


log = logging.getLogger(__name__)


class MinimaxChecker:
    def __init__(
        self,
        endpoint: str,
        api_key: str,
        model: str = "minimax/minimax-m2.5",
        vision_model: str = "",
        skill_context: dict[str, str] | None = None,
        **client_kwargs,
    ):
        self.skill_context = skill_context or {}
        self.client = LLMClient(
            endpoint=endpoint,
            api_key=api_key,
            model=model,
            **client_kwargs,
        )
        self.vision_client = None
        if vision_model:
            self.vision_client = LLMClient(
                endpoint=endpoint,
                api_key=api_key,
                model=vision_model,
                **client_kwargs,
            )

    async def check_vietnamese_tone(self, text: str) -> list[dict]:
        """VT-02..VT-06 — needs context to disambiguate."""
        try:
            system = compose_prompt(load_prompt("vietnamese_tone"), {
                "vietnamese-tone-rules.md": self.skill_context.get("vietnamese-tone-rules", ""),
                "output-format.md": self.skill_context.get("output-format", ""),
            })
            content = await self.client.chat(system=system, user=text)
            data = extract_json(content)
            out = []
            for raw in data.get("issues", []):
                n = normalize_issue(raw, text, default_category="vietnamese_tone")
                if n:
                    out.append(n)
            return out
        except Exception as e:
            log.warning("Minimax tone check failed: %s", e)
            return []

    async def check_homophone_and_context(self, text: str) -> list[dict]:
        """TY-06 homophones, missing words, wrong acronyms — semantic only."""
        try:
            system = compose_prompt(load_prompt("homophone_context"), {
                "typo-rules.md": self.skill_context.get("typo-rules", ""),
                "brand-style-rules.md": self.skill_context.get("brand-style-rules", ""),
                "output-format.md": self.skill_context.get("output-format", ""),
            })
            content = await self.client.chat(system=system, user=text)
            data = extract_json(content)
            out = []
            for raw in data.get("issues", []):
                n = normalize_issue(raw, text, default_category="typo")
                if n:
                    out.append(n)
            return out
        except Exception as e:
            log.warning("Minimax homophone check failed: %s", e)
            return []

    async def check_image_vs_text_report(self, text: str, image_b64: str) -> dict:
        """Multimodal: OCR + cross-check image against caption."""
        if not self.vision_client:
            return {
                "status": "disabled",
                "issues": [],
                "image_text_extracted": "",
                "conflicts_count": 0,
                "error": (
                    "Image checks require a multimodal model. "
                    "Set AI_PLATFORM_VISION_MODEL to a model that supports image input."
                ),
            }

        try:
            system = compose_prompt(load_prompt("image_check"), {
                "SKILL.md": self.skill_context.get("skill-md", ""),
                "output-format.md": self.skill_context.get("output-format", ""),
            })
            user_msg = f"Caption text:\n{text}\n\nĐọc text trong ảnh và so sánh."
            content = await self.vision_client.chat(
                system=system,
                user=user_msg,
                images_b64=[image_b64],
            )
            data = extract_json(content)
            out = []
            for raw in data.get("conflicts", []):
                n = normalize_issue(raw, text, default_category="image_text_conflict")
                if n:
                    # Attach image_text if present
                    if "image_text" in raw:
                        n["image_text"] = raw["image_text"]
                    out.append(n)
            return {
                "status": "ok",
                "model": self.vision_client.model,
                "issues": out,
                "image_text_extracted": data.get("image_text_extracted", ""),
                "conflicts_count": len(out),
                "raw": data,
            }
        except Exception as e:
            log.warning("Minimax image check failed: %s", e)
            return {
                "status": "error",
                "issues": [],
                "image_text_extracted": "",
                "conflicts_count": 0,
                "error": str(e),
            }

    async def check_image_vs_text(self, text: str, image_b64: str) -> list[dict]:
        """Backward-compatible helper returning only conflict issues."""
        report = await self.check_image_vs_text_report(text, image_b64)
        return report.get("issues", [])
