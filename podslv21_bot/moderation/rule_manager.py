from os import listdir
from pathlib import Path
from typing import List


class RuleManager:
    def __init__(self, rules_dir: Path):
        self.rules_dir = rules_dir
        self.rules: List[str] = []

    def reload(self):
        if not self.rules_dir.is_dir():
            return

        self.rules.clear()
        for rule_filename in listdir(self.rules_dir):
            rule_file = Path(self.rules_dir / rule_filename).resolve()
            with rule_file.open(encoding="utf-8") as f:
                self.rules.append(f.read())

    def get_rules(self):
        return self.rules