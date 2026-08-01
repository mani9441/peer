from typing import Dict, Any, Optional
from jinja2.sandbox import SandboxedEnvironment

class PromptRenderer:
    """
    Renders Jinja2 templates safely and calculates size metrics.
    """
    
    def __init__(self):
        self.env = SandboxedEnvironment()

    def render(self, template_body: str, placeholders: Dict[str, Any]) -> str:
        """
        Renders a Jinja2 template body with the given placeholder dictionary.
        """
        try:
            template = self.env.from_string(template_body)
            return template.render(**placeholders)
        except Exception as e:
            raise RuntimeError(f"Rendering failed: {str(e)}")

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimates the number of tokens based on character length.
        Standard rule of thumb: 1 token is ~4 characters.
        """
        if not text:
            return 0
        return max(1, int(len(text) / 4.0))

    @classmethod
    def get_metrics(cls, text: str) -> Dict[str, Any]:
        """
        Computes textual complexity metrics (characters, words, estimated tokens).
        """
        if not text:
            return {
                "char_count": 0,
                "word_count": 0,
                "token_estimate": 0
            }
        return {
            "char_count": len(text),
            "word_count": len(text.split()),
            "token_estimate": cls.estimate_tokens(text)
        }
