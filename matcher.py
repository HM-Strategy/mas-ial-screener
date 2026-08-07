import re
import rapidfuzz.fuzz

LEGAL_SUFFIXES = [
    'PTE LTD', 'PTE. LTD.', 'PTE LTD.', 'PTE.LTD', 'PRIVATE LIMITED',
    'LTD', 'LIMITED', 'LLC', 'L.L.C.', 'LLP', 'L.L.P.', 'INC', 'INCORPORATED',
    'CORP', 'CORPORATION', 'SDN BHD', 'BHD', 'GMBH', 'AG', 'SA', 'S.A.',
    'PLC', 'LP', 'L.P.', 'SPC', 'VCC', 'LTD.', 'CO', 'CO.', 'COMPANY',
    'HOLDINGS', 'HOLDING', 'GROUP', 'INTERNATIONAL', 'INTL',
    'ASIA PACIFIC', 'APAC', 'SINGAPORE', 'SG',
]

_SUFFIX_PATTERN = re.compile(
    r'\b(?:' + '|'.join(re.escape(s) for s in sorted(LEGAL_SUFFIXES, key=len, reverse=True)) + r')\.?\s*',
    re.IGNORECASE
)


def normalize_name(name: str) -> str:
    normalized = name.upper()
    normalized = _SUFFIX_PATTERN.sub('', normalized)
    normalized = re.sub(r'[(){}\[\]]', '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    return normalized


def match_single(client_name: str, ial_entries: list[dict], threshold: int = 85) -> dict | None:
    norm_client = normalize_name(client_name)

    for entry in ial_entries:
        norm_entry_name = normalize_name(entry["name"])

        # 1. EXACT match
        if norm_client == norm_entry_name:
            return {
                "match": True,
                "client_name": client_name,
                "matched_entry": entry,
                "confidence": 100,
                "match_type": "exact"
            }

        # 2. ALIAS match
        for alias in entry.get("aliases", []):
            if normalize_name(alias) == norm_client:
                return {
                    "match": True,
                    "client_name": client_name,
                    "matched_entry": entry,
                    "confidence": 100,
                    "match_type": "alias"
                }

        # 3. SUBSTRING match (both names >= 10 chars after normalization)
        if len(norm_client) >= 5 and len(norm_entry_name) >= 5:
            if norm_client in norm_entry_name or norm_entry_name in norm_client:
                return {
                    "match": True,
                    "client_name": client_name,
                    "matched_entry": entry,
                    "confidence": 90,
                    "match_type": "substring"
                }

        # 4. FUZZY match
        score = rapidfuzz.fuzz.token_sort_ratio(norm_client, norm_entry_name)
        if score >= threshold:
            return {
                "match": True,
                "client_name": client_name,
                "matched_entry": entry,
                "confidence": score,
                "match_type": "fuzzy"
            }

    return None


def match_batch(client_names: list[str], ial_entries: list[dict], threshold: int = 85) -> list[dict]:
    results = []
    for name in client_names:
        result = match_single(name, ial_entries, threshold)
        if result is not None:
            results.append(result)
    results.sort(key=lambda r: r["confidence"], reverse=True)
    return results
