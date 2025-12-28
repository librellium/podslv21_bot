import inspect
import json
import logging
from json import JSONDecodeError
from typing import Any, Dict, List, Optional, Union

from openai import APIResponseValidationError, AsyncOpenAI

from anonflow.config import Config

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
                {"name": func.__name__, "args": args, "description": func.__doc__ or ""}
            )

        function_names = self.get_function_names()

        if "moderation_decision" not in function_names:
            self._logger.warning(
                "Critical function 'moderation_decision' not found. Running the bot in this mode is NOT recommended!"
            )

        self._logger.info(
            f"Functions added: {', '.join(function_names)}. Total={len(self._functions)}"
        )

    def get_function_names(self) -> List[str]:
        return [name for f in self._functions if (name := f.get("name"))]

    async def plan(
        self, text: Optional[str] = None, image: Optional[str] = None
    ) -> List[Dict[str, Union[list, str]]]:
        if not self.moderation:
            return [
                {
                    "name": "moderation_decision",
                    "args": ["APPROVE", "Модерация выключена."]
                }
            ]

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
                    return [
                        {
                            "name": "moderation_decision",
                            "args": ["REJECT", "Сообщение заблокировано автомодератором."]
                        }
                    ]

        if "gpt" in self.config.moderation.types and text:
            funcs = self._functions
            funcs_prompt = "\n".join(
                f"- {func['name']}({', '.join(f'{arg}: {ann}' for arg, ann in (func.get('args') or {}).items())})"
                f" - {func.get('description', '')}"
                for func in funcs
            )

            retry = 0
            result = None

            while retry <= self._client.max_retries:
                response = await self._client.responses.create(
                    model=self.config.moderation.model,
                    input=[
                        {
                            "role": "system",
                            "content": "Respond strictly with a JSON array in the following format:\n"
                            '`[{"name": ..., "args": [...]} , ...]`\n'
                            "`name` - the function name, `args` - an ordered list of arguments.\n"
                            "Output only a valid JSON. Choose functions based on the user's request and the function descriptions.\n"
                            "You are allowed to call multiple functions, listing them in order in the output.\n\n"
                            "**IMPORTANT:**\n"
                            "- Each function must include **all and only the required arguments** specified in its description.\n"
                            "- Do not invent additional arguments.\n"
                            "- Do not omit required arguments.\n"
                            "- `args` must be in the order specified in the function description.\n\n"
                            "Available functions:\n"
                            f"{funcs_prompt}",
                        },
                        *[
                            {"role": "system", "content": rule}
                            for rule in self.rule_manager.get_rules()
                        ],
                        {"role": "user", "content": text},
                    ],
                )

                try:
                    text = response.output_text

                    start = text.index("[")
                    end = text.rindex("]") + 1

                    result = json.loads(text[start:end])
                    break
                except JSONDecodeError:
                    retry += 1

            if not result:
                raise APIResponseValidationError()

            return result

        return [
            {
                "name": "moderation_decision",
                "args": ["APPROVE", "Модераторы не сработали."],
            }
        ]
