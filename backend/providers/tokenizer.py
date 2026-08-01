from typing import Optional
import tiktoken

class Tokenizer:
    @staticmethod
    def estimate_tokens(text: str, model_name: Optional[str] = None) -> int:
        """
        Estimates the number of tokens in the given text.
        If tiktoken fails or model is not found, falls back to a simple character count method.
        """
        if not text:
            return 0
            
        try:
            if model_name:
                clean_model = model_name.split("/")[-1].lower()
                if "gpt" in clean_model:
                    # Let's map model to a known encoding
                    if "gpt-4" in clean_model or "gpt-3.5" in clean_model:
                        encoding = tiktoken.encoding_for_model(clean_model)
                    else:
                        encoding = tiktoken.get_encoding("cl100k_base")
                else:
                    encoding = tiktoken.get_encoding("cl100k_base")
            else:
                encoding = tiktoken.get_encoding("cl100k_base")
                
            return len(encoding.encode(text))
        except Exception:
            # Fallback character estimation: average of 4 characters per token
            return max(1, int(len(text) / 4.0))
