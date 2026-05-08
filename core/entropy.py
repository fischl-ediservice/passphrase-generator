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
    Kryptografisch sicheres Stride-Sampling.

    1. Fisher-Yates Shuffle des gesamten Pools (secrets)
    2. Zufälliger Startpunkt x (crypto rand)
    3. Zufällige Schrittlänge y (crypto rand, mind. 1)
    4. Traversierung: pos → pos+y
       Überlauf: Reflexion am Ende → pos = (N-1) - ((pos+y) - N)
       = 2*(N-1) - pos - y  (Spiegelpunkt, kein Modulo-Sprung)
    5. Bei Zyklus ohne k Treffer: Fallback auf secure_sample

    Gegenüber reinem secure_sample: gleichmäßigere Abdeckung des
    Pools über die gesamte Breite, kein Clustering.
    """
    pool = list(seq)
    n    = len(pool)
    if k >= n:
        return pool

    # Schritt 1: Pool shufflen (Fisher-Yates mit secrets)
    for i in range(n - 1, 0, -1):
        j = secrets.randbelow(i + 1)
        pool[i], pool[j] = pool[j], pool[i]

    # Schritt 2+3: Startpunkt und Schrittlänge
    x = secrets.randbelow(n)          # 0 … n-1
    y = secrets.randbelow(n - 1) + 1  # 1 … n-1

    # Schritt 4: Stride mit Reflexion
    result  = []
    visited = set()
    pos     = x

    seen_positions: set[int] = set()
    cycles_without_new = 0

    while len(result) < k:
        # Wort eintragen falls noch nicht besucht
        if pos not in visited:
            result.append(pool[pos])
            visited.add(pos)
            cycles_without_new = 0
        else:
            cycles_without_new += 1

        # Abbruch bei Zyklus (alle erreichbaren Positionen erschöpft)
        if cycles_without_new > n:
            break

        # Nächste Position berechnen
        next_pos = pos + y

        # Reflexion am oberen Ende
        if next_pos >= n:
            next_pos = 2 * (n - 1) - next_pos
            y = -y

        # Reflexion am unteren Ende
        if next_pos < 0:
            next_pos = -next_pos
            y = -y

        # Degenerierten Einzel-Zyklus erkennen
        if next_pos == pos:
            break

        pos = next_pos

    # Fallback: fehlende Wörter zufällig ergänzen
    if len(result) < k:
        remaining = [pool[i] for i in range(n) if i not in visited]
        result.extend(secure_sample(remaining, min(k - len(result), len(remaining))))

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
