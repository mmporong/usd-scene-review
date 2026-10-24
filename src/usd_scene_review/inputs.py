"""UI input validation before review ownership or previous evidence is cleared."""
from pathlib import Path


def manifest_inputs(values):
    paths = {}
    for side, role in (('A', 'baseline/before'), ('B', 'revision/after')):
        text = values.get(side, '').strip()
        if len(text) >= 2 and text[0] == text[-1] and text[0] in ('"', "'"):
            text = text[1:-1].strip()
        if not text:
            raise ValueError(f'{side} {role}: choose a frozen snapshot manifest.json, not a source USD file.')
        path = Path(text).expanduser().resolve()
        if not path.is_file():
            raise ValueError(f'{side} {role}: manifest file does not exist. Check the path; no install is required.')
        if path.suffix.lower() in ('.usd', '.usda', '.usdc', '.usdz'):
            raise ValueError(f'{side} {role}: select manifest.json inside the frozen snapshot bundle, not the source USD.')
        paths[side] = path
    return paths
