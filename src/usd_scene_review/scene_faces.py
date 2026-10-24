"""Bounded static old-A faces for SceneUI; no USD authoring or renderer material."""
from pxr import Gf
from .ghost import extract,FACE_COLOR,FACE_OPACITY,WIRE_COLOR
from .polygon_faces import triangulate,Budget

MAX_TRIANGLES=20000


def old_faces(snapshot,path):
    def unsupported(reason):return {'status':'unsupported','reason':reason,'meshes':[],'wires':[],'triangles':0}
    data=extract(snapshot,path,max_prims=64,max_points=10000)
    if data['status']!='ready':return unsupported(data['reason'])
    meshes=[];triangles=0;wires=[];budget=Budget()
    for item in data['geometry']:
        attrs=item['attributes']
        if item['type']=='Cube':
            half=float(attrs['size'][1])/2
            points=[[half if n&(1<<axis) else -half for axis in range(3)] for n in range(8)]
            quads=((0,2,3,1),(4,5,7,6),(0,1,5,4),(2,6,7,3),(0,4,6,2),(1,3,7,5))
            faces=[tri for a,b,c,d in quads for tri in ((a,b,c),(a,c,d))]
            orientation=str(attrs.get('orientation',(None,'rightHanded'))[1])
            if orientation not in ('rightHanded','leftHanded'):return unsupported('Invalid Cube orientation')
            if orientation=='leftHanded':faces=[(a,c,b) for a,b,c in faces]
            edges={tuple(sorted(pair)) for face in quads for pair in zip(face,face[1:]+face[:1])}
        else:
            if str(attrs.get('subdivisionScheme',(None,'catmullClark'))[1])!='none':
                return unsupported('SceneUI faces require a linear Mesh (subdivisionScheme none); no control-cage substitute')
            points=attrs['points'][1];counts=attrs['faceVertexCounts'][1];indices=attrs['faceVertexIndices'][1]
            holes=list(attrs.get('holeIndices',(None,[]))[1])
            if len(set(holes))!=len(holes) or any(hole<0 or hole>=len(counts) for hole in holes):
                return unsupported('Invalid Mesh hole indices')
            orientation=str(attrs.get('orientation',(None,'rightHanded'))[1])
            if orientation not in ('rightHanded','leftHanded'):return unsupported('Invalid Mesh orientation')
            holes=set(holes);faces=[];edges=set();start=0
            for index,count in enumerate(counts):
                if index not in holes:
                    if triangles+len(faces)+count-2>MAX_TRIANGLES:return unsupported('SceneUI faces exceed 20000 triangles')
                    ring=[int(v) for v in indices[start:start+count]]
                    if orientation=='leftHanded':ring.reverse()
                    try:faces.extend(triangulate(points,ring,budget))
                    except ValueError as exc:return unsupported(str(exc))
                    edges.update(tuple(sorted(pair)) for pair in zip(ring,ring[1:]+ring[:1]))
                start+=count
        triangles+=len(faces)
        if triangles>MAX_TRIANGLES:return unsupported('SceneUI faces exceed 20000 triangles')
        matrix=Gf.Matrix4d(*[value for row in item['world'] for value in row])
        # Output has no USD orientation token. Encode the effective winding in
        # the triangles, including the opposite-handed rule for mirrored worlds.
        if matrix.GetDeterminant()<0:faces=[(a,c,b) for a,b,c in faces]
        positions=[list(matrix.Transform(Gf.Vec3d(*point))) for point in points]
        if len(wires)//2+len(edges)>20000:return unsupported('SceneUI face outlines exceed 20000 segments')
        # SceneUI receives independent face vertices, matching its bundled sample;
        # keep the source topology only for deduplicated perimeter wire cues.
        expanded=[positions[index] for face in faces for index in face]
        if faces:meshes.append({'positions':expanded,'colors':[list((*FACE_COLOR,FACE_OPACITY)) for _ in expanded],
            'vertex_counts':[3]*len(faces),'vertex_indices':list(range(len(expanded)))})
        for a,b in sorted(edges):wires.extend((positions[a],positions[b]))
    if not meshes:return unsupported('No nonhole old-A faces')
    return {'status':'ready','reason':'Static old A UI faces; unlit overlay without scene depth/materials',
            'meshes':meshes,'wires':wires,'wire_color':(*WIRE_COLOR,1.),'triangles':triangles}
