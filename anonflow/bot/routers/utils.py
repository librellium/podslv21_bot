from typing import Optional

def rm_post(text: Optional[str]):
    if not text:
        return ""

    cmd, *rest = text.lstrip().split(maxsplit=1)
    if cmd.lower() == "/post":
        return " ".join(rest)

    return text
