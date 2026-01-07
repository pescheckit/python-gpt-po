import logging
import os
from typing import Dict, List, Optional, Tuple

import polib

try:
    import tiktoken
except ImportError:
    tiktoken = None


class CostEstimator:
    """Estimates token usage and costs for translation tasks."""

    # Pricing per 1,000 tokens (Input price, Output price)
    # Data sourced from provider websites (Jan 2026)
    PRICING = {
        "gpt-4o": (0.0025, 0.010),
        "gpt-4o-mini": (0.00015, 0.0006),
        "claude-3-5-sonnet": (0.003, 0.015),
        "claude-3-5-sonnet-20241022": (0.003, 0.015),
        "deepseek-chat": (0.00014, 0.00028),
        "deepseek-v3": (0.00014, 0.00028),
    }

    OUTPUT_MULTIPLIER = 1.3  # Conservative estimate for translation expansion

    @classmethod
    def estimate_cost(
        cls,
        folder: str,
        languages: List[str],
        model: str,
        fix_fuzzy: bool = False,
        respect_gitignore: bool = True
    ) -> Dict:
        """
        Estimate token usage and cost for Issue #57.
        Algorithm: tokenize(unique msgids once) * count(target languages) * pricing
        """
        from .gitignore import create_gitignore_parser
        from .po_entry_helpers import is_entry_untranslated

        # 1. Collect all untranslated msgids once (Offline scan)
        unique_msgids = set()
        gitignore_parser = create_gitignore_parser(folder, respect_gitignore)

        for root, dirs, files in os.walk(folder):
            dirs[:], files = gitignore_parser.filter_walk_results(root, dirs, files)
            for file in files:
                if file.endswith('.po'):
                    file_path = os.path.join(root, file)
                    try:
                        po = polib.pofile(file_path)
                        for entry in po:
                            if is_entry_untranslated(entry) or (fix_fuzzy and 'fuzzy' in entry.flags):
                                if entry.msgid:
                                    unique_msgids.add(entry.msgid)
                    except Exception as e:
                        logging.warning("Error reading %s for estimation: %s", file_path, e)

        # 2. Tokenize the entire source content once
        combined_text = "".join(unique_msgids)
        source_tokens = cls._get_token_count(combined_text, model)

        # 3. Calculate total tokens (including expansion)
        total_input_tokens = source_tokens * len(languages)
        total_output_tokens = int(total_input_tokens * cls.OUTPUT_MULTIPLIER)
        total_tokens = total_input_tokens + total_output_tokens

        # 4. Lookup price for model
        pricing_data = cls._get_pricing(model.lower())
        estimated_cost = None
        rate_info = "unavailable"

        if pricing_data:
            in_p, out_p = pricing_data
            cost_in = (total_input_tokens / 1000) * in_p
            cost_out = (total_output_tokens / 1000) * out_p
            estimated_cost = cost_in + cost_out
            rate_info = f"${in_p:.5f} (in) / ${out_p:.5f} (out) per 1K tokens"

        # 5. Calculate breakdown
        breakdown = {}
        for lang in languages:
            lang_in = source_tokens
            lang_out = int(source_tokens * cls.OUTPUT_MULTIPLIER)
            lang_total = lang_in + lang_out
            lang_cost = None
            if pricing_data:
                lang_cost = ((lang_in / 1000) * in_p) + ((lang_out / 1000) * out_p)
            breakdown[lang] = {
                "tokens": lang_total,
                "cost": lang_cost
            }

        return {
            "total_tokens": total_tokens,
            "estimated_cost": estimated_cost,
            "rate_info": rate_info,
            "model": model,
            "num_languages": len(languages),
            "unique_texts": len(unique_msgids),
            "breakdown": breakdown
        }

    @staticmethod
    def _get_token_count(text: str, model: str) -> int:
        """Approximate token count using tiktoken or heuristic."""
        if not text:
            return 0
        if tiktoken:
            try:
                try:
                    encoding = tiktoken.encoding_for_model(model)
                except KeyError:
                    encoding = tiktoken.get_encoding("cl100k_base")
                return len(encoding.encode(text))
            except Exception:
                pass
        # Fallback heuristic
        return max(1, len(text) // 4)

    @classmethod
    def _get_pricing(cls, model: str) -> Optional[Tuple[float, float]]:
        """Lookup pricing for the active model name."""
        return cls.PRICING.get(model)
