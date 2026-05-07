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
