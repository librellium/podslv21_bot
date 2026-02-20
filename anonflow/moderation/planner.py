import inspect
import json
import logging
import textwrap
from typing import Any, Dict, FrozenSet, List, Optional, Union

from httpx import AsyncClient
from httpx._types import ProxyTypes
from httpx._urls import URL
from openai import AsyncOpenAI, OpenAIError

from anonflow.config.models import ModerationBackend

from .exceptions import (
    ModerationError,
    ModerationNoAvailableFunctionsError,
    ModerationOutputParseError
)
from .rule_manager import RuleManager


class ModerationPlanner:
    def __init__(
        self,
        api_key: Optional[str],
        gpt_model: str,
        backends: FrozenSet[ModerationBackend],
        rule_manager: RuleManager,
        *,
        base_url: Optional[Union[str, URL]] = None,
        proxy: Optional[ProxyTypes] = None,
        timeout: Optional[float] = None,
        max_retries: int = 2,
    ):
        self._logger = logging.getLogger(__name__)

        self._gpt_model = gpt_model
        self._backends = backends
        self._max_retries = max_retries

        self._client = AsyncClient(proxy=proxy)

        self._openai_client = None
        self._openai_params = {
            "api_key": api_key,
            "base_url": base_url,
            "timeout": timeout,
            "max_retries": self._max_retries,
            "http_client": self._client
        }

        self.rule_manager = rule_manager

        self._functions: List[Dict[str, Any]] = []

    @staticmethod
    def _approve(reason: str):
        return [{
            "name": "moderation_decision",
            "args": {
                "status": "approve",
                "reason": reason
            }
        }]

    @staticmethod
    def _reject(reason: str):
        return [{
            "name": "moderation_decision",
            "args": {
                "status": "reject",
                "reason": reason
            }
        }]

    @staticmethod
    def _build_content(text: Optional[str] = None, image: Optional[str] = None):
        content = []
        if text:
            content.append({
                "type": "text",
                "text": text
            })
        if image:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image}"
                }
            })

        return content

    @staticmethod
    def _build_functions_prompt(functions: List[Dict[str, Any]]) -> str:
        lines = []

        for func in functions:
            args = ", ".join(
                f"{arg}: {ann}"
                for arg, ann in func.get("args", {}).items()
            )

            line = f"- {func['name']}({args})"

            if func.get("description"):
                line += f" — {func['description']}"

            lines.append(line)

        return "\n".join(lines)

    async def _run_omni(self, text: Optional[str] = None, image: Optional[str] = None):
        if self.is_backend_enabled("omni"):
            content = self._build_content(text, image)

            if content:
                moderation = await self._openai_client.moderations.create(
                    model="omni-moderation-latest", input=content
                )

                return moderation.results[0].flagged

        return False

    async def _run_gpt(self, text: Optional[str] = None):
        if not text:
            return

        if self.is_backend_enabled("gpt"):
            functions_prompt = self._build_functions_prompt(self._functions)

            output = None
            for attempt in range(self._max_retries + 1):
                try:
                    response = await self._openai_client.responses.create(
                        model=self._gpt_model,
                        input=[
                            {
                                "role": "system",
                                "content": textwrap.dedent(
                                    f'''
                                    Respond strictly with a JSON array in the following format:
                                    `[{{"name": ..., "args": {{...}}}}, ...]`
                                    `name` - the function name, `args` - dict of arguments.
                                    Output only a valid JSON. Choose functions based on the user's request and the function descriptions.
                                    You are allowed to call multiple functions, listing them in order in the output.

                                    **IMPORTANT:**
                                    - Each function must include **all and only the required arguments** specified in its description.
                                    - Do not invent additional arguments.
                                    - Do not omit required arguments.
                                    Available functions:
                                    {functions_prompt}
                                    '''
                                ).strip(),
                            },
                            {
                                "role": "system",
                                "content": "\n\n".join(self.rule_manager.get_rules())
                            },
                            {
                                "role": "user",
                                "content": text
                            }
                        ]
                    )
                except OpenAIError as e:
                    raise ModerationError() from e

                try:
                    output = json.loads(response.output_text)

                    if not isinstance(output, list) or not all(isinstance(obj, dict) for obj in output):
                        raise ModerationOutputParseError()

                    break
                except (ValueError, ModerationOutputParseError):
                    self._logger.warning(
                        "Failed to parse response. Attempt %d/%d.",
                        attempt + 1,
                        self._max_retries + 1,
                    )

            if output is None:
                raise ModerationOutputParseError()

            return output

    async def close(self):
        if self._openai_client:
            await self._openai_client.close()
        await self._client.aclose()

    def is_backend_enabled(self, backend: ModerationBackend):
        return (
            backend in self._backends
            and self._enabled
            and self._openai_client is not None
        )

    def set_enabled(self, value: bool, *, api_key: Optional[str] = None):
        self._enabled = value

        if not getattr(self._openai_client, "api_key", None) and api_key:
            self._openai_params["api_key"] = api_key

        if value and not self._openai_client:
            if not self._openai_params.get("api_key"):
                raise ValueError("api_key is required to enable moderation")
            self._openai_client = AsyncOpenAI(**self._openai_params)

    def set_functions(self, *functions):
        if not functions:
            return

        self._functions.clear()
        for func in functions:
            sig = inspect.signature(func)
            args = {
                name: (
                    getattr(param.annotation, "__name__", str(param.annotation))
                    if param.annotation != inspect._empty else "str"
                )
                for name, param in sig.parameters.items()
            }

            self._functions.append(
                {"name": func.__name__, "args": args, "description": func.description or ""}
            )

        function_names = self.get_function_names()

        if "moderation_decision" not in function_names:
            self._logger.warning(
                "Critical function 'moderation_decision' not found. Running the bot in this mode is NOT recommended!"
            )

        self._logger.info(
            f"Functions set: {', '.join(function_names)}. Total={len(self._functions)}"
        )

    def get_function_names(self) -> List[str]:
        return [f["name"] for f in self._functions if "name" in f]

    async def plan(self, text: Optional[str] = None, image: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self._enabled:
            return self._approve("Moderation is disabled.")

        if not self._functions:
            raise ModerationNoAvailableFunctionsError()

        if await self._run_omni(text, image):
            return self._reject("Message was rejected by the auto-moderator.")

        output = await self._run_gpt(text)
        if output:
            return output

        return self._approve("Moderators weren't triggered.")
