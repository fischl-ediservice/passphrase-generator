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

    1. Fisher-Yates Shuffle des gesamten Pools (secrets)
    2. Krypto-zufälliger Startpunkt x  (0 … N-1)
    3. Krypto-zufällige Schrittlänge y (1 … N-1)
    4. Element an pos entnehmen (Pool schrumpft)
       Nächste pos = pos + y
       Überlauf: next_pos -= N  (N = Größe VOR der Entnahme)

    Beispiel: N=100, pos=90, y=20
      → next = 110, overflow → 110-100 = 10, Pool jetzt 99
      → next = 10+20 = 30, Pool jetzt 98 …
    """
    pool = list(seq)
    n    = len(pool)
    if k >= n:
        return pool

    # Schritt 1: Fisher-Yates Shuffle
    for i in range(n - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        pool[i], pool[j] = pool[j], pool[i]

    # Schritt 2+3
    pos = secrets.randbelow(n)          # 0 … N-1
    y   = secrets.randbelow(n - 1) + 1  # 1 … N-1

    result: list = []

    while len(result) < k and pool:
        pos = pos % len(pool)           # Sicherheitsnetz falls y > aktuelle Poolgröße
        n_before = len(pool)
        result.append(pool.pop(pos))
        next_pos = pos + y
        if next_pos >= n_before:
            next_pos -= n_before
        pos = next_pos

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
