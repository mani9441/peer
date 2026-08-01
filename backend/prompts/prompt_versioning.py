import difflib
from typing import List

class PromptVersioning:
    """
    Handles prompt version number increments and template diff generation.
    """
    
    @staticmethod
    def get_diff(body_a: str, body_b: str, name_a: str = "Version A", name_b: str = "Version B") -> str:
        """
        Generates a unified text diff between two template bodies.
        """
        lines_a = (body_a or "").splitlines()
        lines_b = (body_b or "").splitlines()
        
        diff = difflib.unified_diff(
            lines_a,
            lines_b,
            fromfile=name_a,
            tofile=name_b,
            lineterm=""
        )
        return "\n".join(list(diff))

    @staticmethod
    def increment_version(current_ver: str) -> str:
        """
        Increments a version string. Handles numeric strings or 'v'-prefixed strings.
        e.g., "1" -> "2", "v1" -> "v2".
        """
        current_ver = str(current_ver).strip()
        if current_ver.isdigit():
            return str(int(current_ver) + 1)
        
        if current_ver.lower().startswith("v") and current_ver[1:].isdigit():
            prefix = current_ver[0]
            num = int(current_ver[1:])
            return f"{prefix}{num + 1}"
            
        return f"{current_ver}_next"
