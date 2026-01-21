#!/usr/bin/env python3
"""
GROQ API MANAGER
Automatically switches between multiple Groq API keys when quota is exhausted.
Provides seamless failover for uninterrupted operation.
"""

import toml
from groq import Groq
from typing import Optional, List


class GroqManager:
    """
    Smart Groq client that automatically switches API keys on quota errors.
    """

    def __init__(self, secrets_path: str = '.streamlit/secrets.toml'):
        """Initialize with all available Groq API keys."""
        self.secrets_path = secrets_path
        self.api_keys = self._load_api_keys()
        self.current_key_index = 0
        self.client = None
        self._initialize_client()

    def _load_api_keys(self) -> List[str]:
        """Load all Groq API keys from secrets."""
        secrets = toml.load(self.secrets_path)
        keys = []

        # Primary key
        if 'GROQ_API_KEY' in secrets:
            keys.append(secrets['GROQ_API_KEY'])

        # Secondary keys (GROQ_API_KEY_2, GROQ_API_KEY_3, etc.)
        i = 2
        while f'GROQ_API_KEY_{i}' in secrets:
            keys.append(secrets[f'GROQ_API_KEY_{i}'])
            i += 1

        if not keys:
            raise ValueError("No Groq API keys found in secrets")

        print(f"[OK] Loaded {len(keys)} Groq API key(s)")
        return keys

    def _initialize_client(self):
        """Initialize Groq client with current key."""
        current_key = self.api_keys[self.current_key_index]
        self.client = Groq(api_key=current_key)
        key_preview = current_key[:8] + "..." + current_key[-4:]
        print(f"[KEY] Using Groq API key #{self.current_key_index + 1}: {key_preview}")

    def _switch_to_next_key(self) -> bool:
        """
        Switch to next available API key.

        Returns: True if switched successfully, False if no more keys
        """
        if self.current_key_index + 1 >= len(self.api_keys):
            print("[WARNING] All Groq API keys exhausted")
            return False

        self.current_key_index += 1
        self._initialize_client()
        print(f"[REFRESH] Switched to Groq API key #{self.current_key_index + 1}")
        return True

    def chat_completions_create(self, **kwargs):
        """
        Wrapper for Groq chat.completions.create with automatic failover.

        Automatically switches keys if quota error occurs.
        """
        max_attempts = len(self.api_keys)

        for attempt in range(max_attempts):
            try:
                response = self.client.chat.completions.create(**kwargs)
                return response

            except Exception as e:
                error_str = str(e).lower()

                # Check if this is a quota/rate limit error
                if any(keyword in error_str for keyword in ['quota', 'rate limit', 'limit exceeded', '429']):
                    print(f"[WARNING] Quota exhausted on key #{self.current_key_index + 1}")

                    # Try switching to next key
                    if self._switch_to_next_key():
                        print(f"[REFRESH] Retrying with key #{self.current_key_index + 1}...")
                        continue  # Retry with new key
                    else:
                        # No more keys available
                        raise Exception(f"All {len(self.api_keys)} Groq API keys exhausted") from e
                else:
                    # Not a quota error, re-raise immediately
                    raise

        # Should never reach here
        raise Exception("Max retry attempts reached")


# Global instance (singleton pattern)
_groq_manager_instance: Optional[GroqManager] = None


def get_groq_client():
    """
    Get global GroqManager instance.

    Usage:
        groq_client = get_groq_client()
        response = groq_client.chat_completions_create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": "Hello"}]
        )
    """
    global _groq_manager_instance

    if _groq_manager_instance is None:
        _groq_manager_instance = GroqManager()

    return _groq_manager_instance


# Testing
if __name__ == "__main__":
    print("Testing Groq Manager\n")

    manager = GroqManager()

    print(f"\nTotal API keys loaded: {len(manager.api_keys)}")
    print(f"Current key index: {manager.current_key_index}")

    # Test switching
    if len(manager.api_keys) > 1:
        print("\nTesting key switching...")
        manager._switch_to_next_key()
        print(f"New key index: {manager.current_key_index}")

    print("\n[OK] Groq Manager ready for automatic failover")
