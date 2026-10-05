"""Resource Fingerprinter for computing atomic and hierarchical Merkle digests.

Supports:
- Atomic digests for individual normalized text fields or primitive values
- Ordered sequence digests (Merkle sequence) preserving exact item order
- Unordered set digests (order-independent) for discovering permuted collections
- Compound multi-attribute digests (Merkle tree) combining named component digests
"""

from __future__ import annotations

import hashlib
from collections.abc import Sequence

from .models import ContentFingerprint
from .normalizer import TextNormalizer


class ResourceFingerprinter:
    """Computes deterministic cryptographic fingerprints and Merkle digests."""

    def __init__(
        self,
        normalizer: TextNormalizer | None = None,
        default_digest_length: int = 16,
    ) -> None:
        """Initializes ResourceFingerprinter.

        Args:
            normalizer: Optional TextNormalizer for preprocessing text.
            default_digest_length: Truncation length for SHA-256 digests (16 by default).
                Pass 0 or 64 for full SHA-256 hex string.
        """
        self.normalizer = normalizer or TextNormalizer()
        self.default_digest_length = default_digest_length

    def _truncate_digest(self, full_hex: str, length: int | None = None) -> str:
        """Applies configured truncation to SHA-256 hex digest."""
        target_len = self.default_digest_length if length is None else length
        if target_len > 0:
            return full_hex[:target_len]
        return full_hex

    def digest_text(self, text: str, prefix: str = "", length: int | None = None) -> str:
        """Computes a SHA-256 digest from text with optional prefix."""
        payload = f"{prefix}::{text}" if prefix else text
        full_hex = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return self._truncate_digest(full_hex, length)

    def fingerprint_atomic(
        self,
        raw_text: str | None,
        prefix: str = "",
        normalize: bool = True,
        length: int | None = None,
    ) -> ContentFingerprint:
        """Generates a ContentFingerprint for a single atomic string or primitive."""
        raw = raw_text or ""
        canonical_sig = self.normalizer.normalize(raw) if normalize else raw.strip()
        digest = self.digest_text(canonical_sig, prefix=prefix, length=length)

        return ContentFingerprint(
            digest=digest,
            signature=canonical_sig,
        )

    def fingerprint_ordered_sequence(
        self,
        item_digests: Sequence[str],
        prefix: str = "ORDERED",
        length: int | None = None,
    ) -> str:
        """Computes a Merkle digest preserving the exact sequence of child digests."""
        payload = ";;".join(item_digests)
        return self.digest_text(payload, prefix=prefix, length=length)

    def fingerprint_unordered_set(
        self,
        item_digests: Sequence[str],
        prefix: str = "SET",
        length: int | None = None,
    ) -> str:
        """Computes an order-independent Merkle digest by sorting child digests canonically."""
        sorted_digests = sorted(item_digests)
        payload = ";;".join(sorted_digests)
        return self.digest_text(payload, prefix=prefix, length=length)

    def fingerprint_compound(
        self,
        components: dict[str, str],
        prefix: str = "COMPOUND",
        length: int | None = None,
    ) -> ContentFingerprint:
        """Computes a Merkle compound digest from a dictionary of named component digests.

        Args:
            components: Mapping of component names to their individual digests.
            prefix: Prefix for the compound digest.
            length: Optional digest length override.

        Returns:
            ContentFingerprint containing the composite digest and component map.
        """
        # Sort by component name for deterministic combination
        sorted_entries = [f"{k}={v}" for k, v in sorted(components.items()) if v]
        canonical_signature = ";".join(sorted_entries)
        compound_digest = self.digest_text(canonical_signature, prefix=prefix, length=length)

        return ContentFingerprint(
            digest=compound_digest,
            signature=canonical_signature,
            component_digests=components,
        )

    def fingerprint_collection(
        self,
        child_fingerprints: Sequence[ContentFingerprint],
        signature_label: str = "",
        length: int | None = None,
    ) -> ContentFingerprint:
        """Generates both ordered and unordered fingerprints for a collection of resources."""
        digests = [fp.digest for fp in child_fingerprints]
        ordered_dig = self.fingerprint_ordered_sequence(digests, length=length)
        unordered_dig = self.fingerprint_unordered_set(digests, length=length)

        sig = signature_label or f"collection_size={len(digests)}"
        return ContentFingerprint(
            digest=ordered_dig,  # Primary digest defaults to sequence-preserving
            signature=sig,
            ordered_digest=ordered_dig,
            unordered_digest=unordered_dig,
            component_digests={str(i): d for i, d in enumerate(digests)},
        )
