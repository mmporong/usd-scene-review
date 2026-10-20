"""Verify local resolver behavior, rather than trusting a resolver's Python name."""
import os
from pathlib import Path, PureWindowsPath
from pxr import Ar, Sdf


def local_identifier(identifier):
    """Only native absolute filesystem paths, without URI/package/format arguments."""
    text = str(identifier)
    if not text or any(c in text for c in ('\0', '[', ']', '?', '#')) or text.startswith(('//', '\\\\')):
        raise ValueError('non-local or unverifiable resolved identifier')
    path_text, arguments = Sdf.Layer.SplitIdentifier(text)
    if arguments:
        raise ValueError('resolver file-format arguments unsupported')
    drive = PureWindowsPath(path_text).drive
    if ':' in path_text and not (os.name == 'nt' and len(drive) == 2 and drive[1] == ':' and path_text.count(':') == 1):
        raise ValueError('URI or non-native resolved identifier unsupported')
    path = Path(path_text)
    if not path.is_absolute():
        raise ValueError('resolver did not return an absolute local path')
    return path


def require_same_file(identifier, expected):
    actual = local_identifier(identifier)
    # Inspect the lexical path too: resolve() alone would conceal junctions/symlinks.
    for component in (actual, *actual.parents):
        if component.exists() and (component.is_symlink() or getattr(component.lstat(), 'st_file_attributes', 0) & 0x400):
            raise ValueError('resolved path uses symlink or reparse point')
    if actual.resolve() != expected.resolve():
        raise ValueError('resolver remapped a pinned local file')
    return actual


def check_absolute(path):
    resolver = Ar.GetResolver()
    require_same_file(resolver.CreateIdentifier(str(path), Ar.ResolvedPath(str(path))), path)
    require_same_file(resolver.Resolve(str(path)), path)


def check_layer(layer, expected):
    if layer.anonymous:
        raise ValueError('anonymous source layer unsupported')
    require_same_file(layer.identifier, expected)
    require_same_file(layer.realPath, expected)
    check_absolute(expected)


def check_dependency(layer, reference, expected):
    if (not reference or ':' in reference or PureWindowsPath(reference).drive
            or reference.startswith(('/', '\\')) or any(c in reference for c in ('\0', '[', ']', '?', '#'))):
        raise ValueError('non-local or package dependency unsupported')
    resolver = Ar.GetResolver()
    anchored = resolver.CreateIdentifier(reference, Ar.ResolvedPath(layer.realPath))
    require_same_file(anchored, expected)
    require_same_file(Sdf.ComputeAssetPathRelativeToLayer(layer, reference), expected)
    require_same_file(resolver.Resolve(anchored), expected)


def used_layer_errors(stage, base, files):
    """Composed layers must be exact pinned files, except the owned anonymous session."""
    errors = []
    session = stage.GetSessionLayer()
    pinned_paths = {(base / rel).resolve(): rel for rel in files}
    if len(pinned_paths) != len(files):
        errors.append('ambiguous aliases in pinned dependency closure')
    if not session.anonymous:
        errors.append('review session is not anonymous')
    for layer in stage.GetUsedLayers():
        if layer == session:
            continue
        try:
            path = local_identifier(layer.realPath).resolve()
            try:
                relative = path.relative_to(base.resolve()).as_posix()
            except ValueError:
                raise ValueError('composed layer is outside the pinned dependency closure') from None
            relative = pinned_paths.get(path)
            if relative is None:
                raise ValueError('composed layer is outside the pinned dependency closure')
            check_layer(layer, base / relative)
            if layer.dirty:
                errors.append('source layer dirty')
        except Exception as error:
            message = str(error) if isinstance(error, ValueError) else 'resolver API failed'
            errors.append('unverified composed layer: ' + message)
    return errors
