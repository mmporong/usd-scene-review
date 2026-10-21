"""Bounded static old-A geometry for a visual-only anonymous-session overlay."""
import math
from pxr import Gf, Sdf, Usd, UsdGeom, UsdShade
from .measurements import affine

MESH_ATTRIBUTES = ('points','faceVertexCounts','faceVertexIndices','subdivisionScheme','orientation',
                   'doubleSided','holeIndices','creaseIndices','creaseLengths','creaseSharpnesses',
                   'cornerIndices','cornerSharpnesses','interpolateBoundary',
                   'faceVaryingLinearInterpolation','triangleSubdivisionRule','normals','extent')
FACE_OPACITY = .22
FACE_COLOR = (.12, .95, .22)
WIRE_COLOR = (.025, .42, .035)
MAX_WIRE_SEGMENTS = 20000


def wire_points(data):
    """Cube edges and Mesh control-cage edges, not a computed silhouette."""
    result=[]
    for item in data['geometry']:
        matrix=Gf.Matrix4d(*[x for row in item['world'] for x in row])
        attrs=item['attributes']
        if item['type']=='Cube':
            size=float(attrs['size'][1])/2
            points=[Gf.Vec3d(*[size if n & (1 << i) else -size for i in range(3)]) for n in range(8)]
            edges=[(n,n^(1<<axis)) for n in range(8) for axis in range(3) if n<(n^(1<<axis))]
        else:
            points=attrs['points'][1];indices=attrs['faceVertexIndices'][1];edges=set();start=0
            for count in attrs['faceVertexCounts'][1]:
                face=indices[start:start+count];start+=count
                for a,b in zip(face,list(face[1:])+[face[0]]):
                    edges.add(tuple(sorted((int(a),int(b)))))
                    if len(edges)>MAX_WIRE_SEGMENTS:return None
            edges=sorted(edges)
        if len(result)//2+len(edges)>MAX_WIRE_SEGMENTS:return None
        for a,b in edges:
            result.extend((matrix.Transform(Gf.Vec3d(*points[a])),matrix.Transform(Gf.Vec3d(*points[b]))))
    return result


def extract(snapshot, selected, *, max_prims=512, max_points=200000):
    stage=snapshot.stage; prim=stage.GetPrimAtPath(selected)
    def unsupported(reason):return {'status':'unsupported','reason':reason,'geometry':[]}
    if not prim or not prim.IsActive() or not prim.IsLoaded():
        return unsupported('Old A selection is absent, inactive or unloaded')
    t=snapshot.manifest['config']['time'];time=Usd.TimeCode.Default() if t=='default' else Usd.TimeCode(float(t))
    image=UsdGeom.Imageable(prim)
    if image and image.ComputeVisibility(time)=='invisible':return unsupported('Old A selection is invisible')
    cache=UsdGeom.XformCache(time);geometry=[];point_count=0
    for p in stage.TraverseAll():
        if not p.GetPath().HasPrefix(prim.GetPath()):continue
        if p.IsInstance() or p.IsInstanceProxy() or p.IsPrototype() or p.IsA(UsdGeom.PointInstancer):
            return unsupported('Instances/prototypes/point instancers are unsupported')
        if not p.IsActive():continue
        if not p.IsLoaded():return unsupported('Unloaded old A geometry is unsupported')
        image=UsdGeom.Imageable(p)
        if image and image.ComputeVisibility(time)=='invisible':continue
        if image and image.ComputePurpose() not in ('default', 'render', 'proxy'):continue
        if not UsdGeom.Gprim(p):continue
        if p.GetTypeName() not in ('Cube','Mesh'):return unsupported('Only static Cube and Mesh geometry is supported')
        ancestor=p
        while ancestor and not ancestor.IsPseudoRoot():
            if (any('Skel' in name or 'Deform' in name for name in ancestor.GetAppliedSchemas())
                    or any('skel:' in prop.GetName().lower() or 'deform' in prop.GetName().lower()
                           for prop in ancestor.GetProperties())):
                return unsupported('Deformed/skinned geometry is unsupported')
            if any(a.GetNumTimeSamples() for a in ancestor.GetAttributes()):
                return unsupported('Animated geometry/ancestor is unsupported')
            ancestor=ancestor.GetParent()
        from .overlap_analysis import has_displacement
        try:
            if has_displacement(p,max_prims):
                return unsupported('Material displacement, including subsets/render contexts, is unsupported')
        except ValueError:
            return unsupported('Material subset budget exceeded')
        matrix=cache.GetLocalToWorldTransform(p)
        values=[[float(x) for x in row] for row in matrix]
        if not affine(values) or abs(matrix.GetDeterminant())<1e-12 or any(abs(x)>1e25 for row in values for x in row):
            return unsupported('Nonfinite, singular or out-of-range old world transform')
        attrs={}
        names=('size','orientation','doubleSided','extent') if p.IsA(UsdGeom.Cube) else MESH_ATTRIBUTES
        for name in names:
            attr=p.GetAttribute(name)
            if attr and attr.Get(time) is not None:attrs[name]=(attr.GetTypeName(),attr.Get(time))
        if p.IsA(UsdGeom.Mesh):
            points=attrs.get('points',(None,[]))[1];counts=attrs.get('faceVertexCounts',(None,[]))[1];indices=attrs.get('faceVertexIndices',(None,[]))[1]
            if (not points or not counts or len(indices)>1000000 or len(counts)>333333
                    or sum(counts)!=len(indices) or any(n<3 for n in counts)
                    or any(i<0 or i>=len(points) for i in indices)
                    or any(not math.isfinite(float(x)) or abs(x)>1e25 for point in points for x in point)):
                return unsupported('Invalid or out-of-range mesh topology/points')
            point_count+=len(points)
            corners=points
        else:
            size=float(attrs['size'][1])
            if not math.isfinite(size) or not 0<size<1e25:return unsupported('Unsupported cube size')
            point_count+=8
            corners=[Gf.Vec3d(x*size/2,y*size/2,z*size/2) for x in (-1,1) for y in (-1,1) for z in (-1,1)]
        if any(not math.isfinite(x) or abs(x)>1e25 for point in corners for x in matrix.Transform(Gf.Vec3d(*point))):
            return unsupported('Transformed old geometry exceeds finite display range')
        if len(geometry)>=max_prims or point_count>max_points:return unsupported('Selected overlay exceeds bounded geometry limits')
        normals=UsdGeom.Mesh(p).GetNormalsInterpolation() if p.IsA(UsdGeom.Mesh) else None
        geometry.append({'source_path':str(p.GetPath()),'type':p.GetTypeName(),'world':values,
                         'attributes':attrs,'normals_interpolation':normals})
    if not geometry:return unsupported('No visible supported old A geometry')
    return {'status':'ready','reason':'Old A visible static Cube/Mesh only','geometry':geometry}


class GhostOverlay:
    def __init__(self,stage,root):
        self.stage=stage;self.root=root.AppendChild('OldPoseGhost')
        if stage.GetEditTarget().GetLayer()!=stage.GetSessionLayer() or not stage.GetSessionLayer().anonymous:
            raise ValueError('Ghost overlay requires the owned anonymous session')
    def clear(self):
        if self.stage.GetPrimAtPath(self.root):self.stage.RemovePrim(self.root)
    def show(self,data,opacity=FACE_OPACITY):
        self.clear()
        if not math.isfinite(opacity) or not 0<opacity<=1:raise ValueError('Invalid ghost opacity')
        if data['status']!='ready':return {'status':'unsupported','reason':data['reason'],'count':0}
        wires=wire_points(data)
        if wires is None:return {'status':'unsupported','reason':'Old A wire cues exceed 20,000 segments','count':0}
        UsdGeom.Scope.Define(self.stage,self.root)
        material=UsdShade.Material.Define(self.stage,self.root.AppendChild('Material'))
        shader=UsdShade.Shader.Define(self.stage,material.GetPath().AppendChild('Surface'))
        # Use the installed SDK's non-refractive cutout template. The qualified
        # RTX PreviewSurface route darkened overlapping ghosts in real captures.
        shader.SetSourceAsset(Sdf.AssetPath('OmniPBR.mdl'),'mdl')
        shader.SetSourceAssetSubIdentifier('OmniPBR','mdl')
        shader.CreateInput('diffuse_color_constant',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*FACE_COLOR))
        shader.CreateInput('enable_opacity',Sdf.ValueTypeNames.Bool).Set(True)
        shader.CreateInput('enable_opacity_texture',Sdf.ValueTypeNames.Bool).Set(False)
        shader.CreateInput('opacity_constant',Sdf.ValueTypeNames.Float).Set(opacity)
        shader.CreateInput('opacity_threshold',Sdf.ValueTypeNames.Float).Set(0)
        shader.CreateInput('reflection_roughness_constant',Sdf.ValueTypeNames.Float).Set(1)
        shader.CreateInput('specular_level',Sdf.ValueTypeNames.Float).Set(0)
        shader.CreateInput('enable_emission',Sdf.ValueTypeNames.Bool).Set(False)
        shader.CreateOutput('out',Sdf.ValueTypeNames.Token)
        material.CreateSurfaceOutput('mdl').ConnectToSource(shader.ConnectableAPI(),'out')
        for i,item in enumerate(data['geometry']):
            path=self.root.AppendChild('Geometry_'+str(i))
            geom=UsdGeom.Cube.Define(self.stage,path) if item['type']=='Cube' else UsdGeom.Mesh.Define(self.stage,path)
            for name,(kind,value) in item['attributes'].items():geom.GetPrim().CreateAttribute(name,kind).Set(value)
            # Avoid accumulating both front and back faces of each old solid.
            geom.CreateDoubleSidedAttr(False)
            if item['normals_interpolation']:geom.SetNormalsInterpolation(item['normals_interpolation'])
            # Local geometry + exactly one complete A world matrix; no inherited
            # source ancestor transform, reset-stack inference or TRS decomposition.
            matrix=Gf.Matrix4d(*[x for row in item['world'] for x in row])
            UsdGeom.Xformable(geom).MakeMatrixXform().Set(matrix)
            UsdShade.MaterialBindingAPI.Apply(geom.GetPrim()).Bind(material)
        wire_material=UsdShade.Material.Define(self.stage,self.root.AppendChild('WireMaterial'))
        wire_shader=UsdShade.Shader.Define(self.stage,wire_material.GetPath().AppendChild('Surface'))
        wire_shader.CreateIdAttr('UsdPreviewSurface')
        wire_shader.CreateInput('diffuseColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*WIRE_COLOR))
        wire_shader.CreateInput('roughness',Sdf.ValueTypeNames.Float).Set(1)
        wire_shader.CreateInput('useSpecularWorkflow',Sdf.ValueTypeNames.Int).Set(1)
        wire_shader.CreateInput('specularColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0))
        wire_shader.CreateInput('emissiveColor',Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(0))
        wire_material.CreateSurfaceOutput().ConnectToSource(wire_shader.ConnectableAPI(),'surface')
        lo=Gf.Vec3d(*[min(p[i] for p in wires) for i in range(3)])
        hi=Gf.Vec3d(*[max(p[i] for p in wires) for i in range(3)])
        width=max((hi-lo).GetLength()*.0006,1e-6)
        curves=UsdGeom.BasisCurves.Define(self.stage,self.root.AppendChild('WireCues'))
        curves.CreateTypeAttr('linear');curves.CreateWrapAttr('nonperiodic')
        curves.CreateCurveVertexCountsAttr([2]*(len(wires)//2))
        curves.CreatePointsAttr([Gf.Vec3f(*p) for p in wires]);curves.CreateWidthsAttr([width])
        curves.SetWidthsInterpolation('constant')
        UsdShade.MaterialBindingAPI.Apply(curves.GetPrim()).Bind(wire_material)
        return {'status':'shown','count':len(data['geometry']),'opacity':opacity,
                'wire_segments':len(wires)//2,'wire_width_stage_units':width,
                'face_color':list(FACE_COLOR),'opacity_threshold':0.0,
                'technique':'translucent green fractional-cutout single-sided faces + subtle control-cage edges; no emission',
                'reason':'Old A translucent surface helper; current B retains original materials. Visual only; no physics copied.'}
