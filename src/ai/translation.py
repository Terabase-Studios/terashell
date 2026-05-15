from dataclasses import dataclass
from typing import Optional

import ai
from ai import ChatSession, RequestConfig


@dataclass
class CommandTranslationConfig:
    max_tokens: int = 128
    temperature: float = 0.1
    top_p: float = 1.0


def translate_to_command(
    request: str,
    os: str = "UNKNOWN",
    cwd: str = "UNKNOWN",
    config: Optional[CommandTranslationConfig] = None,
) -> str:

    config = config or CommandTranslationConfig()

    session = ChatSession()

    session.system(
        f"""
        You are a shell command generator.
        
        Convert natural language into ONE shell command.
        
        Rules:
        - Output ONLY the command.
        - No explanations.
        - No markdown.
        - No code blocks.
        - No comments.
        - No numbering.
        - Prefer safe commands.
        - Never use sudo unless explicitly requested.
        - Never use destructive commands unless explicitly requested.
        - Target OS: {os}
        - Target shell: Terashell
        - Use sudo before command if super user required or requested.
        
        If impossible, output nothing
        """
    )

    session.user(
                f"""
        Current Directory:
        {cwd}
        
        Request:
        {request}
        """
    )

    result = ai.AI_INTERFACE.chat(
        session,
        RequestConfig(
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=config.top_p,
        )
    )

    return clean_command(result)


def clean_command(text: str) -> str:

    text = text.strip()

    # remove code fences
    text = text.replace("```powershell", "")
    text = text.replace("```bash", "")
    text = text.replace("```cmd", "")
    text = text.replace("```", "")

    # first non-empty line only
    for line in text.splitlines():
        line = line.strip()

        if line:
            return line

    return ""


if __name__ == "__main__":
    ai.init()
    cmd = translate_to_command(
    "compress this folder",
    os="Linux",
    )

    print(cmd)