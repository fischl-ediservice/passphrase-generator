import bisect
import math
import secrets


def secure_choice(seq: list) -> object:
    return secrets.choice(seq)


def secure_sample(seq: list, k: int) -> list:
    pool = list(seq)
    result = []
    for _ in range(k):
        idx = secrets.randbelow(len(pool))
        result.append(pool.pop(idx))
    return result


def stride_sample(seq: list, k: int) -> list:
    """
    Kryptografisch sicheres Stride-Sampling mit schrumpfendem Pool.

    1. Alle Wörter liegen in einem Pool.
    2. Krypto-zufälliger Startpunkt x  (0 … N-1)
    3. Krypto-zufällige Schrittlänge y (1 … N-1)
    4. Element an pos entnehmen, Pool schrumpft.
    5. Nächste pos = (pos + y) mod neue Poolgröße.

    Beispiel: N=10, pos=2, y=5
      pop 2, Pool jetzt 9, next = 2+5 = 7
      pop 7, Pool jetzt 8, next = (7+5) mod 8 = 4
      pop 4, Pool jetzt 7, next = (4+5) mod 7 = 2
    """
    return [seq[i] for i in stride_indices(len(seq), k)]


def stride_indices(pool_size: int, k: int) -> list[int]:
    if k <= 0 or pool_size <= 0:
        return []
    if pool_size == 1:
        return [0][:k]

    remaining = pool_size
    pos = secrets.randbelow(pool_size)          # 0 … N-1
    y   = secrets.randbelow(pool_size - 1) + 1  # 1 … N-1

    result: list[int] = []
    removed: list[int] = []

    while len(result) < k and remaining:
        pos = pos % remaining
        original_index = _remaining_rank_to_original_index(pos, removed)
        result.append(original_index)
        bisect.insort(removed, original_index)
        remaining -= 1
        if remaining:
            pos = (pos + y) % remaining

    return result


def _remaining_rank_to_original_index(rank: int, removed: list[int]) -> int:
    original_index = rank
    for removed_index in removed:
        if removed_index <= original_index:
            original_index += 1
        else:
            break
    return original_index


def secure_bool(probability: float = 0.5) -> bool:
    return secrets.randbelow(1_000_000) < int(probability * 1_000_000)


def calculate_entropy(pool_size: int, word_count: int) -> float:
    if pool_size <= 1:
        return 0.0
    return round(word_count * math.log2(pool_size), 2)


def entropy_label(bits: float) -> str:
    if bits >= 100:
        return "sehr stark"
    if bits >= 72:
        return "stark"
    if bits >= 50:
        return "ausreichend"
    return "schwach"
