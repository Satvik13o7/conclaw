from __future__ import annotations

import os
import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv
from openai import AzureOpenAI

from conclaw.llm.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)

load_dotenv(Path.cwd() / ".env")
load_dotenv(Path.home() / ".conclaw" / ".env")


@dataclass
class StreamResult:
    content: str = ""
    tokens_in: int = 0
    tokens_out: int = 0


class LLMClient:
    MAX_RETRIES = 3

    def __init__(self, config: dict) -> None:
        self._config = config
        self._api_key: str | None = None
        self._client: AzureOpenAI | None = None
        self._messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    def _get_api_key(self) -> str:
        if self._api_key:
            return self._api_key

        env_var = self._config.get("api_key_env", "AZURE_OPENAI_KEY")
        key = os.getenv(env_var)
        if key:
            self._api_key = key
            return key

        # Fallback: fetch from Azure Key Vault
        self._api_key = self._fetch_key_from_vault()
        if self._api_key:
            return self._api_key

        raise RuntimeError(
            f"API key not found. Set the {env_var} environment variable, "
            f"add it to a .env file, or configure Key Vault credentials "
            f"(KEYVAULTURL, CLIENT_SECRET) in .env."
        )

    def _fetch_key_from_vault(self) -> str | None:
        vault_url = os.getenv("KEYVAULTURL")
        client_secret = os.getenv("CLIENT_SECRET")
        if not vault_url or not client_secret:
            return None

        try:
            from azure.identity import ClientSecretCredential
            from azure.keyvault.secrets import SecretClient

            tenant_id = os.getenv("TENANT_ID", "33b98860-21ef-4870-9beb-712f0cdac7b9")
            client_id = os.getenv("CLIENT_ID", "44cd8e31-4059-43e1-9cfd-702445642c03")

            credential = ClientSecretCredential(
                tenant_id=tenant_id,
                client_id=client_id,
                client_secret=client_secret,
            )
            client = SecretClient(vault_url=vault_url, credential=credential)
            key = client.get_secret("SWQAOAI-KEY1").value
            logger.info("API key fetched from Key Vault.")
            return key
        except Exception as e:
            logger.warning(f"Key Vault fetch failed: {e}")
            return None

    def _get_client(self) -> AzureOpenAI:
        if self._client is None:
            self._client = AzureOpenAI(
                api_key=self._get_api_key(),
                api_version=self._config.get("azure_api_version", "2025-01-01-preview"),
                azure_endpoint=self._config.get(
                    "azure_endpoint", "https://sw-qa-genai-oai01.openai.azure.com/"
                ),
            )
        return self._client

    @property
    def messages(self) -> list[dict]:
        return self._messages

    def chat(self, user_message: str) -> tuple[str, int, int]:
        self._messages.append({"role": "user", "content": user_message})
        client = self._get_client()
        deployment = self._config.get("azure_deployment", "gpt-4.1")

        for attempt in range(self.MAX_RETRIES):
            try:
                response = client.chat.completions.create(
                    model=deployment,
                    messages=self._messages,
                    temperature=self._config.get("temperature", 0.2),
                    max_tokens=self._config.get("max_tokens", 4096),
                )
                content = response.choices[0].message.content or ""
                self._messages.append({"role": "assistant", "content": content})

                usage = response.usage
                tokens_in = usage.prompt_tokens if usage else 0
                tokens_out = usage.completion_tokens if usage else 0
                return content, tokens_in, tokens_out

            except Exception as e:
                logger.error(f"LLM call failed (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                else:
                    self._messages.pop()
                    raise

    def chat_stream(self, user_message: str, on_chunk: Callable[[str], None]) -> StreamResult:
        """Stream a response, calling on_chunk(text) for each token. Returns final StreamResult."""
        self._messages.append({"role": "user", "content": user_message})
        client = self._get_client()
        deployment = self._config.get("azure_deployment", "gpt-4.1")

        for attempt in range(self.MAX_RETRIES):
            try:
                stream = client.chat.completions.create(
                    model=deployment,
                    messages=self._messages,
                    temperature=self._config.get("temperature", 0.2),
                    max_tokens=self._config.get("max_tokens", 4096),
                    stream=True,
                    stream_options={"include_usage": True},
                )

                result = StreamResult()
                chunks: list[str] = []

                for event in stream:
                    if event.usage:
                        result.tokens_in = event.usage.prompt_tokens
                        result.tokens_out = event.usage.completion_tokens

                    if event.choices and event.choices[0].delta.content:
                        text = event.choices[0].delta.content
                        chunks.append(text)
                        on_chunk(text)

                result.content = "".join(chunks)
                self._messages.append({"role": "assistant", "content": result.content})
                return result

            except Exception as e:
                logger.error(f"LLM stream failed (attempt {attempt + 1}/{self.MAX_RETRIES}): {e}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                else:
                    self._messages.pop()
                    raise

    def reset(self) -> None:
        self._messages = [{"role": "system", "content": SYSTEM_PROMPT}]
