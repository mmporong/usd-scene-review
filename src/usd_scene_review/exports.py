"""Exclusive JSON/HTML evidence export, outside immutable input bundles."""
from pathlib import Path
from .snapshot import canonical
from .cli import render_html


def save_report(report, destination, *, forbidden_roots=()):
    destination = Path(destination).expanduser().resolve()
    if any(destination.is_relative_to(Path(root).resolve()) for root in forbidden_roots):
        raise ValueError('Choose an output folder outside the input snapshot bundles')
    payloads = {'review.json': canonical(report), 'review.html': render_html(report)}
    # A new directory prevents accidental replacement of prior evidence or scenes.
    destination.mkdir(exist_ok=False)
    for name, text in payloads.items():
        with (destination / name).open('x', encoding='utf-8') as stream:
            stream.write(text)
    return destination
