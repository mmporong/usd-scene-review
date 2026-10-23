"""Package only this project's Python/Kit adapter, without NVIDIA binaries."""
from pathlib import Path
import argparse
import zipfile


def package(destination):
    repo = Path(__file__).resolve().parents[1]
    extension = repo / 'exts' / 'mmporong.scene.review'
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise ValueError('destination must be a new file')
    files = {}
    for path in extension.rglob('*'):
        if path.is_file() and '__pycache__' not in path.parts:
            files[path.relative_to(extension).as_posix()] = path.read_bytes()
    config = files['config/extension.toml'].decode('utf-8').replace('path = "../../src"', 'path = "python"')
    files['config/extension.toml'] = config.encode('utf-8')
    # Keep candidate installation/qualification guidance usable after extraction.
    files['docs/in-app-review.md'] = (repo/'docs/in-app-review.md').read_bytes()
    files['docs/in-app-sdk-diagnosis.md'] = (repo/'docs/in-app-sdk-diagnosis.md').read_bytes()
    files['docs/teardown-investigation.md'] = (repo/'docs/teardown-investigation.md').read_bytes()
    files['docs/viewport-reuse-assessment.md'] = (repo/'docs/viewport-reuse-assessment.md').read_bytes()
    files['examples/usd-scene-review-in-app.png'] = (repo/'examples/usd-scene-review-in-app.png').read_bytes()
    files['docs/README.md'] = files['docs/README.md'].replace(
        b'../../../docs/in-app-review.md', b'in-app-review.md')
    for path in (repo / 'src' / 'usd_scene_review').glob('*.py'):
        files['python/usd_scene_review/' + path.name] = path.read_bytes()
    with zipfile.ZipFile(destination, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, content)
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    print(package(args.destination).name)
