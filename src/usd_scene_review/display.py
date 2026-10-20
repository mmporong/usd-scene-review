"""Anonymous-session review display: colored geometry, labelled AABB curves/camera."""
import math
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade

COLORS = {'A': (0.015, 0.23, 0.8), 'B': (1.0, 0.22, 0.015)}


def world_bounds(snapshot, selected):
    prim = snapshot.stage.GetPrimAtPath(selected)
    if not prim or not prim.IsActive() or not prim.IsLoaded():
        return None
    t = snapshot.manifest['config']['time']
    time = Usd.TimeCode.Default() if t == 'default' else Usd.TimeCode(float(t))
    imageable = UsdGeom.Imageable(prim)
    if imageable and imageable.ComputeVisibility(time) == UsdGeom.Tokens.invisible:
        return None
    # Render/default/proxy geometry, respecting composed visibility; no helper prims.
    cache = UsdGeom.BBoxCache(time, [UsdGeom.Tokens.default_, UsdGeom.Tokens.render, UsdGeom.Tokens.proxy])
    extent = cache.ComputeWorldBound(prim).ComputeAlignedRange()
    if extent.IsEmpty():
        return None
    lo, hi = list(extent.GetMin()), list(extent.GetMax())
    if (not all(math.isfinite(x) and abs(x) < 1e30 for x in lo + hi)
            or not math.isfinite(math.dist(lo, hi)) or math.dist(lo, hi) <= 1e-10):
        return None
    return [lo, hi]


def camera_spec(bounds, up_axis):
    if up_axis not in ('Y', 'Z'):
        raise ValueError('Unsupported up axis')
    available = [b for b in bounds.values() if b is not None]
    if any(len(b) != 2 or any(len(row) != 3 for row in b)
           or not all(math.isfinite(x) and abs(x) < 1e30 for row in b for x in row)
           or any(b[0][i] > b[1][i] for i in range(3)) for b in available):
        raise ValueError('Bounds exceed supported finite display range')
    if not available:
        raise ValueError('No visible finite bounds in either revision')
    lo = [min(b[0][i] for b in available) for i in range(3)]
    hi = [max(b[1][i] for b in available) for i in range(3)]
    center = Gf.Vec3d(*[(a+b)/2 for a, b in zip(lo, hi)])
    radius = math.dist(lo, hi)/2
    if not math.isfinite(radius) or radius <= 1e-10:
        raise ValueError('Degenerate or non-finite bounds')
    direction = Gf.Vec3d(1.5, -2, 1.25) if up_axis == 'Z' else Gf.Vec3d(1.5, 1.25, 2)
    direction.Normalize()
    eye = center + direction * (radius*3.2)
    up = Gf.Vec3d(0, 0, 1) if up_axis == 'Z' else Gf.Vec3d(0, 1, 0)
    transform = Gf.Matrix4d().SetLookAt(eye, center, up).GetInverse()
    return dict(transform=[[float(x) for x in row] for row in transform], focal_length=24.0,
                horizontal_aperture=36.0, vertical_aperture=20.25,
                clipping=[max(radius*.001, 1e-7), max(radius*100, 1e-5)], bounds=bounds)


def outline_points(bounds, dashed):
    lo, hi = bounds
    margin = max(math.dist(lo, hi)*.006, 1e-6)
    lo = [x-margin for x in lo]; hi = [x+margin for x in hi]
    corners = [[hi[i] if n & (1 << i) else lo[i] for i in range(3)] for n in range(8)]
    points = []
    for n in range(8):
        for axis in range(3):
            other = n ^ (1 << axis)
            if n >= other:
                continue
            a, b = corners[n], corners[other]
            count = 8 if dashed else 1
            for segment in range(count):
                start = segment/count
                end = (segment + (.6 if dashed else 1))/count
                points.extend([[a[i]+(b[i]-a[i])*t for i in range(3)] for t in (start, end)])
    return points


class ReviewDisplay:
    def __init__(self, stage):
        self.stage = stage
        if not stage.GetSessionLayer().anonymous or stage.GetEditTarget().GetLayer() != stage.GetSessionLayer():
            raise ValueError('Display requires the owned anonymous edit target')
        root = Sdf.Path('/_UsdSceneReviewDisplay')
        while stage.GetPrimAtPath(root):
            root = Sdf.Path(str(root)+'_')
        self.root = root
        UsdGeom.Scope.Define(stage, root)
        self.materials = {name: self.material(name, color) for name, color in
                          [('Context', (.62, .65, .69)), ('A', COLORS['A']), ('B', COLORS['B'])]}
        self.geometry = []
        # Block original bindings in this session only, including ancestor,
        # collection, purpose and subset bindings, before applying review colors.
        for prim in list(stage.Traverse()):
            if prim.GetPath().HasPrefix(root):
                continue
            for relationship in prim.GetRelationships():
                if relationship.GetName().startswith('material:binding'):
                    relationship.SetTargets([])
            if UsdGeom.Gprim(prim):
                self.geometry.append(prim)
        self.style(None, 'A', None)

    def material(self, name, color):
        material = UsdShade.Material.Define(self.stage, self.root.AppendChild(name))
        shader = UsdShade.Shader.Define(self.stage, material.GetPath().AppendChild('Shader'))
        shader.CreateIdAttr('UsdPreviewSurface')
        shader.CreateInput('diffuseColor', Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
        shader.CreateInput('roughness', Sdf.ValueTypeNames.Float).Set(.8)
        shader.CreateInput('metallic', Sdf.ValueTypeNames.Float).Set(0)
        material.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), 'surface')
        return material

    def style(self, selected, side, bounds):
        path = Sdf.Path(selected) if selected else None
        count = 0
        for prim in self.geometry:
            chosen = path is not None and prim.GetPath().HasPrefix(path)
            material = self.materials[side if chosen else 'Context']
            api = UsdShade.MaterialBindingAPI.Apply(prim)
            api.Bind(material, UsdShade.Tokens.strongerThanDescendants)
            if api.ComputeBoundMaterial()[0].GetPath() != material.GetPath():
                raise RuntimeError('Review material override was not confirmed')
            count += int(chosen)
        outline = self.root.AppendChild('SelectedWorldBounds')
        if self.stage.GetPrimAtPath(outline):
            self.stage.RemovePrim(outline)
        if bounds:
            points = outline_points(bounds, side == 'A')
            curves = UsdGeom.BasisCurves.Define(self.stage, outline)
            curves.CreateTypeAttr(UsdGeom.Tokens.linear)
            curves.CreateWrapAttr(UsdGeom.Tokens.nonperiodic)
            curves.CreateCurveVertexCountsAttr([2]*(len(points)//2))
            curves.CreatePointsAttr([Gf.Vec3f(*p) for p in points])
            curves.CreateWidthsAttr([max(math.dist(*bounds)*.006, 1e-6)])
            curves.SetWidthsInterpolation(UsdGeom.Tokens.constant)
            UsdShade.MaterialBindingAPI.Apply(curves.GetPrim()).Bind(self.materials[side])
        return dict(selected_geometry=count, outline='dashed' if side == 'A' else 'solid',
                    label='selected world AABB bounds', color=list(COLORS[side]))

    def set_camera(self, spec, viewport):
        path = self.root.AppendChild('Camera')
        camera = UsdGeom.Camera.Define(self.stage, path)
        camera.CreateFocalLengthAttr(spec['focal_length'])
        camera.CreateHorizontalApertureAttr(spec['horizontal_aperture'])
        camera.CreateVerticalApertureAttr(spec['vertical_aperture'])
        camera.CreateClippingRangeAttr(Gf.Vec2f(*spec['clipping']))
        transform = Gf.Matrix4d(*[x for row in spec['transform'] for x in row])
        xform = UsdGeom.Xformable(camera)
        xform.MakeMatrixXform().Set(transform)
        viewport.camera_path = str(path)
