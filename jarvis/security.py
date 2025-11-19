import re
from typing import Union, Tuple

def sanitize_input(user_input: Union[str, bytes]) -> str:
    """Prevent injection attacks and malicious input.

    This implementation is intentionally conservative for testing purposes.
    """
    if isinstance(user_input, bytes):
        user_input = user_input.decode('utf-8', errors='ignore')

    dangerous_patterns = [
        r'(\brm\s+-rf\b|\bformat\s+\w+:|\bchmod\s+777\b)',
        r'(\|\s*\w+|\&\&\s*\w+)',
        r'(\$\(|`.*?`)',
        r'(\bexec\b|\beval\b|\bimport\b\s*\(|\b__import__\b)'
    ]

    s = user_input
    for pattern in dangerous_patterns:
        s = re.sub(pattern, '[BLOCKED]', s, flags=re.IGNORECASE)

    return s.strip()


class EnterpriseSecurity:
    """Minimal enterprise security helper for testing."""

    def _contains_dangerous_patterns(self, command: str) -> bool:
        patterns = [
            r'\brm\s+-rf\b',
            r'\bformat\s+\w+:',
            r'\bchmod\s+777\b',
            r'\$\(',
            r'`',
            r'\bexec\b',
            r'\beval\b',
        ]
        for p in patterns:
            if re.search(p, command, re.IGNORECASE):
                return True
        return False

    def validate_command_safety(self, command: str) -> Tuple[bool, str]:
        """Comprehensive command safety validation (minimal for tests)."""
        safe_patterns = [
            r'^hello$', r'^status$', r'^help$',
            r'^security\s+status$', r'^performance\s+metrics$'
        ]

        # Normalize to simple lowercase for pattern matching
        cmd = command.strip().lower()
        for pattern in safe_patterns:
            if re.match(pattern, cmd):
                return True, "Command approved"

        if self._contains_dangerous_patterns(command):
            return False, "Command contains dangerous patterns"

        return True, "Command requires additional verification"
