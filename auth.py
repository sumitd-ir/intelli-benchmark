"""
Authentication and header generation for intelliExtract API.

HeaderFactory ensures every request includes the three mandatory X-headers
required by the App Runner instance.
"""

import os
from typing import Dict


class HeaderFactory:
    """
    Produces the mandatory X-headers for intelliExtract API requests.
    Values are read from environment variables to avoid hardcoding secrets.
    """

    ENV_ACCESS_KEY = "INTELLI_ACCESS_KEY"
    ENV_SIGNATURE = "INTELLI_SIGNATURE"
    ENV_SECRET_MESSAGE = "INTELLI_SECRET_MESSAGE"

    def __init__(
        self,
        access_key: str | None = None,
        signature: str | None = None,
        secret_message: str | None = None,
    ) -> None:
        """
        Initialize with explicit values or fall back to environment variables.

        Args:
            access_key: X-Access-Key value (default: INTELLI_ACCESS_KEY env)
            signature: X-Signature value (default: INTELLI_SIGNATURE env)
            secret_message: X-Secret-Message value (default: INTELLI_SECRET_MESSAGE env)
        """
        raw_key = access_key or os.environ.get(self.ENV_ACCESS_KEY, "")
        raw_sig = signature or os.environ.get(self.ENV_SIGNATURE, "")
        raw_msg = secret_message or os.environ.get(self.ENV_SECRET_MESSAGE, "")
        # Strip whitespace so copy-pasted env vars don't cause "Invalid signature"
        self._access_key = raw_key.strip() if isinstance(raw_key, str) else ""
        self._signature = raw_sig.strip() if isinstance(raw_sig, str) else ""
        self._secret_message = raw_msg.strip() if isinstance(raw_msg, str) else ""

    def headers(self) -> Dict[str, str]:
        """
        Return a dict of the three mandatory X-headers for API requests.

        Returns:
            Dict with keys: X-Access-Key, X-Signature, X-Secret-Message
        """
        return {
            "X-Access-Key": self._access_key,
            "X-Signature": self._signature,
            "X-Secret-Message": self._secret_message,
        }

    def is_configured(self) -> bool:
        """Return True if all three header values are non-empty."""
        return bool(
            self._access_key and self._signature and self._secret_message
        )
