import string
import hashlib
from typing import Dict, List, Any

class SparseVectorGenerator:
    """
    Tạo Sparse Vector (BM25/TF) cho tiếng Việt mà không cần thư viện quá nặng.
    Băm (hash) các từ vựng thành index và tính toán tần suất (value).
    """
    
    def __init__(self):
        # Tiền xử lý: loại bỏ dấu câu cơ bản
        self.punctuation_map = str.maketrans('', '', string.punctuation)

    def tokenize(self, text: str) -> List[str]:
        """Tách từ cơ bản cho tiếng Việt. Tạm thời dùng split theo khoảng trắng."""
        if not text:
            return []
        # Chuyển chữ thường, xóa dấu câu
        text = text.lower().translate(self.punctuation_map)
        # Tách từ theo khoảng trắng
        tokens = text.split()
        # Loại bỏ token rỗng
        return [t for t in tokens if t]

    def _hash_token(self, token: str) -> int:
        """Băm một chuỗi thành số nguyên 32-bit dương để dùng làm index cho Qdrant."""
        # Dùng sha256 rồi cắt lấy 4 byte (32 bits)
        hash_bytes = hashlib.sha256(token.encode('utf-8')).digest()
        # Trả về unsigned 32-bit int (phải phù hợp u32 của Qdrant)
        return int.from_bytes(hash_bytes[:4], byteorder='big')

    def generate_sparse_vector(self, text: str) -> Dict[str, Any]:
        """
        Sinh vector thưa (indices và values).
        Ở đây dùng TF (Term Frequency) làm trọng số cơ bản.
        Returns:
            {"indices": [int, ...], "values": [float, ...]}
        """
        tokens = self.tokenize(text)
        if not tokens:
            return {"indices": [], "values": []}

        # Đếm tần suất
        tf_counts = {}
        for token in tokens:
            tf_counts[token] = tf_counts.get(token, 0) + 1

        indices = []
        values = []

        for token, count in tf_counts.items():
            index = self._hash_token(token)
            
            # Xử lý trường hợp hiếm: collision (2 từ hash ra cùng 1 index)
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
