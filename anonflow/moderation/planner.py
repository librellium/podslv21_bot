import copy
import inspect
import json
import logging
import textwrap
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from anonflow.config import Config

from .exceptions import (
    ModerationPlannerNoAvailableFunctionsError,
    ModerationPlannerParseError
)
from .rule_manager import RuleManager


class ModerationPlanner:
    def __init__(self, config: Config, rule_manager: RuleManager):
        self._logger = logging.getLogger(__name__)

        self.config = config
        self.rule_manager = rule_manager

        api_key = self.config.openai.api_key
        if not api_key:
            raise ValueError("openai.api_key is required and cannot be empty")

        self._client = AsyncOpenAI(
            api_key=api_key.get_secret_value(),
            timeout=self.config.openai.timeout,
            max_retries=self.config.openai.max_retries,
        )
        self.moderation = self.config.moderation.enabled

        self._functions: List[Dict[str, Any]] = []

    def set_functions(self, *functions):
        if not functions:
            return

        self._functions.clear()
        for func in functions:
            sig = inspect.signature(func)
            args = {
                name: (
                    str(param.annotation)
                    if param.annotation != inspect._empty
                    else "str"
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

    def get_functions(self):
        return copy.deepcopy(self._functions)

    def get_function_names(self) -> List[str]:
        return [f["name"] for f in self._functions if "name" in f]

    @staticmethod
    def build_functions_prompt(functions: List[Dict[str, Any]]) -> str:
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

    async def plan(self, text: Optional[str] = None, image: Optional[str] = None):
        if not self.moderation:
            return [{
                "name": "moderation_decision",
                "args": {
                    "status": "approve",
                    "reason": "Модерация выключена."
                }
            }]

        if not self.get_functions():
            raise ModerationPlannerNoAvailableFunctionsError()

        if "omni" in self.config.moderation.types:
            content = []
            if text:
                content.append({"type": "text", "text": text})
            if image:
                content.append({"type": "image_url", "image_url": {"url": image}})

            if content:
                moderation = await self._client.moderations.create(
                    model="omni-moderation-latest", input=content
                )

                if moderation.results[0].flagged:
                    return [{
                        "name": "moderation_decision",
                        "args": {
                            "status": "reject",
                            "reason": "Сообщение заблокировано автомодератором."
                        }
                    }]

        if "gpt" in self.config.moderation.types and text:
            functions = self.get_functions()
            functions_prompt = self.build_functions_prompt(functions)

            output = None
            for attempt in range(self._client.max_retries + 1):
                response = await self._client.responses.create(
                    model=self.config.moderation.model,
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
                        {"role": "user", "content": text},
                    ]
                )

                try:
                    output = json.loads(response.output_text)

                    if not isinstance(output, list) or not all(isinstance(obj, dict) for obj in output):
                        raise ModerationPlannerParseError()

                    break
                except (ValueError, ModerationPlannerParseError):
                    self._logger.warning(
                        "Failed to parse response. Attempt %d/%d.",
                        attempt + 1,
                        self._client.max_retries + 1,
                    )

            if output is None:
                raise ModerationPlannerParseError()

            return output

        return [{
            "name": "moderation_decision",
            "args": {
                "status": "approve",
                "reason": "Модераторы не сработали."
            }
        }]
