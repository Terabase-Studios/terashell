from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from openai import OpenAI
from yaspin import yaspin

AI_INTERFACE: AIInterface
working_locks = []

@dataclass
class ModelInfo:
    id: str
    created: Optional[int] = None
    owned_by: Optional[str] = None


@dataclass
class RequestConfig:
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    stream: bool = False
    top_p: float = 1.0


@dataclass
class ChatSession:
    messages: List[Dict[str, str]] = field(default_factory=list)

    def add(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def user(self, content: str) -> None:
        self.add("user", content)

    def assistant(self, content: str) -> None:
        self.add("assistant", content)

    def system(self, content: str) -> None:
        self.add("system", content)

    def clear(self) -> None:
        self.messages.clear()


@dataclass
class AutocompleteConfig:
    max_tokens: int = 128
    temperature: float = 0.15
    top_p: float = 1.0


# noinspection PyTypeChecker
class AIInterface:

    def __init__(
        self,
        base_url: str,
        api_key: str = "not-needed",
        timeout: float = 120.0,
    ) -> None:

        if not api_key:
            api_key = "not-needed"

        self.client = OpenAI(
            base_url=base_url.rstrip("/") + "/v1",
            api_key=api_key,
            timeout=timeout,
        )

        self.current_model: Optional[str] = None
        self.loaded_model: Optional[str] = None
        self._model_cache: List[ModelInfo] = []

    # =========================================================
    # MODELS
    # =========================================================

    def get_models(self) -> List[ModelInfo]:
        if not self._model_cache:
            return self.refresh_models()
        return self._model_cache


    def print_models(self) -> None:
        """
        Pretty-print available models.
        """

        models = self.get_models()

        if not models:
            print("No models found.")
            return

        print("\nAvailable Models:\n")

        for i, model in enumerate(models):
            print(f"[{i}] {model.id}")


    def select_model(self, model_name: str, preload: bool = True) -> None:
        available = [m.id for m in self.get_models()]

        if model_name not in available:
            raise ValueError(f"Unknown model: {model_name}")

        self.current_model = model_name

        if preload and self.loaded_model != model_name:
            self._preload_model()
            self.loaded_model = model_name


    def refresh_models(self) -> List[ModelInfo]:
        models = self.client.models.list()

        self._model_cache = [
            ModelInfo(
                id=m.id,
                created=getattr(m, "created", None),
                owned_by=getattr(m, "owned_by", None),
            )
            for m in models.data
        ]

        return self._model_cache


    def _preload_model(self) -> None:
        if not self.current_model:
            raise RuntimeError("No model selected")

        self.client.chat.completions.create(
            model=self.current_model,
            messages=[{"role": "user", "content": " "}],
            max_tokens=1,
        )


    # =========================================================
    # CHAT
    # =========================================================

    def chat(
        self,
        session: ChatSession,
        config: Optional[RequestConfig] = None,
    ) -> str:

        if not self.current_model:
            raise RuntimeError("No model selected")

        working_locks.append(session)
        config = config or RequestConfig()

        response = self.client.chat.completions.create(
            model=self.current_model,
            messages=session.messages,
            temperature=config.temperature,
            max_tokens=config.max_tokens,
            top_p=config.top_p,
            stream=config.stream,
        )

        if config.stream:
            full = ""

            for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta:
                    full += delta
                    print(delta, end="", flush=True)

            print()
            return full

        index = working_locks.index(session)
        if index != -1:
            working_locks.pop(index)

        return response.choices[0].message.content or ""


    def autocomplete(
        self,
        prefix: str,
        config: Optional[AutocompleteConfig] = None,
        os="UNKNOWN", cwd="UNKNOWN", nearby_files="UNKNOWN", history_text: str="UNKNOWN",
    ) -> List[str]:

        if not self.current_model:
            raise RuntimeError("No model selected")

        config = config or AutocompleteConfig()

        working_locks.append(config)

        prefix = prefix.rstrip()

        context = (
            f"OS: {os}\n"
            f"Shell: TeraShell\n"
            f"Current Directory: {cwd}\n\n"
            f"Nearby Files:\n{nearby_files}\n\n"
            f"Recent Commands:\n{history_text}\n\n"
            f"Current Input:\n{prefix}"
        )

        response = self.client.chat.completions.create(
            model=self.current_model,
            messages=[
            {
                "role": "system",
                "content": (
                    "You are a shell autocomplete engine.\n"
                    "\n"
                    "Generate multiple likely shell command completions.\n"
                    "\n"
                    "Rules:\n"
                    "- Output ONLY completions.\n"
                    "- One completion per line.\n"
                    "- No markdown.\n"
                    "- No explanations.\n"
                    "- No numbering.\n"
                    "- No bullet points.\n"
                    "- Each completion must begin with the user's current input.\n"
                    "- Prefer realistic and commonly used commands.\n"
                    "- Generate diverse completions.\n"
                )
            },
                {
                    "role": "user",
                    "content": context
                }
            ],
            temperature=0.0,
            top_p=1.0,
            max_tokens=config.max_tokens,
        )

        raw = response.choices[0].message.content or ""

        #print("RAW:", repr(raw))

        completions = []
        seen = set()

        for line in raw.splitlines():

            line = line.strip()

            if not line:
                continue

            # Remove markdown/code fences
            if line.startswith(("```", "-", "*")):
                continue

            # Remove numbering
            if "." in line[:4]:
                parts = line.split(".", 1)

                if len(parts) == 2 and parts[0].isdigit():
                    line = parts[1].strip()

            # Remove quotes
            line = line.strip("\"'")

            # Ignore obvious junk
            if len(line) < 1:
                continue

            # Ignore duplicates
            if line in seen:
                continue

            seen.add(line)

            completions.append(line)

        index = working_locks.index(config)
        if index != -1:
            working_locks.pop(index)

        return completions[:8]


    # =========================================================
    # RAW REQUEST
    # =========================================================

    def raw_chat(self, messages: List[Dict[str, Any]], **kwargs) -> Any:
        if not self.current_model:
            raise RuntimeError("No model selected")

        return self.client.chat.completions.create(
            model=self.current_model,
            messages=messages,
            **kwargs,
        )


def init() -> None:
    global AI_INTERFACE
    import config
    from config import AI_SERVER_IP
    from config import AI_API_KEY
    from config import AI_MODEL

    config.AI_ENABLED = True
    try:
        with yaspin(text=f"Connecting to {AI_SERVER_IP}...", color="yellow") as spinner:
            AI_INTERFACE = AIInterface(AI_SERVER_IP, AI_API_KEY)
            AI_INTERFACE.select_model(AI_MODEL, preload=False)
    except KeyboardInterrupt:
        print(f"Retrieving model interrupted...")
        config.AI_ENABLED = False
        return
    except Exception as e:
        print(f"Error retrieving model {AI_MODEL} from {AI_SERVER_IP}: {e}")
        config.AI_ENABLED = False
        return
    else:
        print(f"Connected to {AI_SERVER_IP}")

    try:
        with yaspin(text=f"Loading AI model {AI_MODEL}...", color="yellow") as spinner:
            AI_INTERFACE.select_model(AI_MODEL, preload=True)
    except KeyboardInterrupt:
        print(f"Loading model interrupted")
        config.AI_ENABLED = False
    except Exception as e:
        print(f"Error loading model: {e}")
        config.AI_ENABLED = False
    else:
        print(f"Loaded {AI_MODEL}")


def is_working() -> bool:
    return len(working_locks) > 0


if __name__ == "__main__":

    ai = AIInterface(
        base_url="http://127.0.0.1:11434",
        api_key="ollama",
    )

    ai.print_models()

    print("Loading Model")
    ai.select_model("small:latest")
    print("Model Loaded\n")

    print("--- autocomplete ---")
    result = ai.autocomplete("systemctl")

    for cmd in result:
        print(cmd)