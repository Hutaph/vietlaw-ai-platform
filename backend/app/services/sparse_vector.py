import string
import hashlib
from typing import Dict, List, Any

class SparseVectorGenerator:
    """
    Generate lightweight sparse vectors for Vietnamese text.
    Tokens are hashed into Qdrant-compatible indexes with TF-style values.
    """
    
    def __init__(self):
        # Precompute punctuation removal for simple tokenization.
        self.punctuation_map = str.maketrans('', '', string.punctuation)

    def tokenize(self, text: str) -> List[str]:
        """Tokenize Vietnamese text with a lightweight whitespace splitter."""
        if not text:
            return []
        # Lowercase and remove basic punctuation.
        text = text.lower().translate(self.punctuation_map)
        # Split on whitespace.
        tokens = text.split()
        # Drop empty tokens.
        return [t for t in tokens if t]

    def _hash_token(self, token: str) -> int:
        """Hash a token into a positive 32-bit integer for Qdrant."""
        # Use sha256 and keep the first 4 bytes.
        hash_bytes = hashlib.sha256(token.encode('utf-8')).digest()
        # Return an unsigned 32-bit integer compatible with Qdrant.
        return int.from_bytes(hash_bytes[:4], byteorder='big')

    def generate_sparse_vector(self, text: str) -> Dict[str, Any]:
        """
        Generate sparse vector indexes and values.
        This implementation uses term frequency as the base weight.
        Returns:
            {"indices": [int, ...], "values": [float, ...]}
        """
        tokens = self.tokenize(text)
        if not tokens:
            return {"indices": [], "values": []}

        # Count token frequency.
        tf_counts = {}
        for token in tokens:
            tf_counts[token] = tf_counts.get(token, 0) + 1

        indices = []
        values = []

        for token, count in tf_counts.items():
            index = self._hash_token(token)
            
            # Handle the rare case where two tokens hash to the same index.
            if index in indices:
                idx_pos = indices.index(index)
                values[idx_pos] += float(count)
            else:
                indices.append(index)
                values.append(float(count))

        return {
            "indices": indices,
            "values": values
        }
