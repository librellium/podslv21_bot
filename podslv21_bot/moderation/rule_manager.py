import logging
from os import listdir
from pathlib import Path
from typing import List


class RuleManager:
    def __init__(self, rules_dir: Path):
        self._logger = logging.getLogger("podslv21_bot.moderation.rule_manager")

        self.rules_dir = rules_dir
        self._rules: List[str] = []

    def reload(self):
        if not self.rules_dir.is_dir():
            return

        self._rules.clear()
        for rule_filename in listdir(self.rules_dir):
            rule_file = Path(self.rules_dir / rule_filename).resolve()
            with rule_file.open(encoding="utf-8") as f:
                rule = f.read()
                if rule:
                    self._rules.append(rule)

        self._logger.info(f"Rules loaded total={len(self._rules)}")

    def get_rules(self):
        return self._rules