def decode(encoded: str, precision: int = 6) -> list[tuple[float, float]]:
    """Decode an encoded polyline into (lat, lon) pairs."""
    factor = 10**precision
    points = []
    index = lat = lon = 0

    def next_delta() -> int:
        nonlocal index
        result = shift = 0
        while True:
            chunk = ord(encoded[index]) - 63
            index += 1
            result |= (chunk & 0x1F) << shift
            shift += 5
            if chunk < 0x20:
                break
        return ~(result >> 1) if result & 1 else result >> 1

    while index < len(encoded):
        lat += next_delta()
        lon += next_delta()
        points.append((lat / factor, lon / factor))
    return points
