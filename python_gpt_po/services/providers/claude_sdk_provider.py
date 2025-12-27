"""
Claude SDK provider implementation.
Uses claude-agent-sdk with Claude Code CLI for authentication.
"""
import logging
import sys
from typing import List

from ...models.provider_clients import ProviderClients
from .base import ModelProviderInterface


class ClaudeSdkProvider(ModelProviderInterface):
    """Claude SDK model provider implementation using claude-agent-sdk."""

    def get_models(self, provider_clients: ProviderClients) -> List[str]:
        """Retrieve available models from Claude SDK."""
        return [
            "claude-opus-4-5-20251101",
            "claude-sonnet-4-5-20250929",
            "claude-3-7-sonnet-latest",
            "claude-3-5-sonnet-20241022",
            "claude-opus-4-1-20250805",
            "claude-haiku-4-5-20251001",
            "claude-3-5-haiku-latest",
        ]

    def get_default_model(self) -> str:
        """Get the default Claude SDK model."""
        return "claude-3-5-haiku-latest"

    def get_preferred_models(self, task: str = "translation") -> List[str]:
        """Get preferred Claude SDK models for a task."""
        if task == "translation":
            return [
                "claude-sonnet-4-5-20250929",
                "claude-3-7-sonnet-latest",
                "claude-3-5-sonnet-20241022"
            ]
        return [self.get_default_model()]

    def is_client_initialized(self, provider_clients: ProviderClients) -> bool:
        """Check if Claude SDK client is initialized."""
        return True

    def get_fallback_models(self) -> List[str]:
        """Get fallback models for Claude SDK."""
        return [
            "claude-sonnet-4-5-20250929",
            "claude-3-7-sonnet-latest",
            "claude-haiku-4-5-20251001",
        ]

    def translate(self, provider_clients: ProviderClients, model: str, content: str) -> str:
        """Get response from Claude SDK using claude-agent-sdk.

        Uses async-to-sync bridge to integrate async SDK with synchronous workflow.
        """
        if not self.is_client_initialized(provider_clients):
            raise ValueError("Claude SDK client not initialized")

        import anyio
        from claude_agent_sdk import (
            AssistantMessage,
            CLINotFoundError,
            ClaudeAgentOptions,
            ProcessError,
            TextBlock,
            query,
        )

        async def get_translation():
            """Async function to get translation from Claude SDK."""
            options = ClaudeAgentOptions(
                model=model,
                max_turns=1
            )

            texts = []
            async for message in query(prompt=content, options=options):
                if not isinstance(message, AssistantMessage):
                    continue

                for block in message.content:
                    if not isinstance(block, TextBlock):
                        continue
                    texts.append(block.text)

            return ''.join(texts).strip()

        try:
            return anyio.run(get_translation)
        except CLINotFoundError as e:
            raise ValueError(
                "Claude Code CLI not found. "
                "Install with: npm install -g @anthropic-ai/claude-code"
            ) from e
        except ProcessError as e:
            raise ValueError(f"Claude Code CLI failed: {e}") from e
