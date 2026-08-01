import json
from typing import Dict, Any

class StrategyVersioning:
    """
    Handles prompt strategy configuration version naming increments and serialization.
    """

    @staticmethod
    def increment_version(current_ver: str) -> str:
        """
        Increments version strings, supporting numbers or 'v'-prefixes.
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

    @staticmethod
    def serialize_config(config_dict: Dict[str, Any]) -> str:
        """Serializes configuration dictionary to string."""
        return json.dumps(config_dict, indent=2)

    @staticmethod
    def deserialize_config(config_str: str) -> Dict[str, Any]:
        """Deserializes configuration string back to dictionary."""
        return json.loads(config_str)
