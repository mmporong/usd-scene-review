"""Conservative deterministic ear clipping of simple planar USD face rings."""
import math

MAX_FACE_VERTICES=256
MAX_OPERATIONS=1000000
EPS=1e-10
PLANAR_EPS=1e-7


class Budget:
    def __init__(self,limit=MAX_OPERATIONS):self.remaining=limit
    def tick(self):
        self.remaining-=1
        if self.remaining<0:raise ValueError('Polygon triangulation operation budget exceeded')


def triangulate(points,ring,budget=None):
    budget=budget if budget is not None else Budget()
    if not 3<=len(ring)<=MAX_FACE_VERTICES:raise ValueError('Polygon face requires 3..256 vertices')
    if len(set(ring))!=len(ring):raise ValueError('Polygon repeated vertex index')
    if any(type(index) is not int or index<0 or index>=len(points) for index in ring):raise ValueError('Polygon invalid vertex index')
    source=[[float(value) for value in points[index]] for index in ring]
    if any(len(point)!=3 or not all(math.isfinite(v) for v in point) for point in source):raise ValueError('Polygon nonfinite/invalid points')
    origin=source[0];relative=[[v-origin[axis] for axis,v in enumerate(point)] for point in source]
    scale=max(abs(v) for point in relative for v in point)
    if not math.isfinite(scale) or scale==0:raise ValueError('Polygon degenerate range')
    p=[[v/scale for v in point] for point in relative]
    for i,a in enumerate(p):
        for b in p[i+1:]:
            budget.tick()
            if sum((a[k]-b[k])**2 for k in range(3))<=EPS**2:raise ValueError('Polygon coincident vertices')
    normal=[sum(a[(axis+1)%3]*b[(axis+2)%3]-a[(axis+2)%3]*b[(axis+1)%3]
        for a,b in zip(p,p[1:]+p[:1])) for axis in range(3)]
    length=math.sqrt(sum(v*v for v in normal))
    if length<=EPS:raise ValueError('Polygon degenerate area or self-intersection')
    normal=[v/length for v in normal]
    if any(abs(sum(v*n for v,n in zip(point,normal)))>PLANAR_EPS for point in p):raise ValueError('Polygon nonplanar face')
    drop=max(range(3),key=lambda axis:abs(normal[axis]));q=[tuple(v for axis,v in enumerate(point) if axis!=drop) for point in p]
    def cross(a,b,c):
        budget.tick();return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    def on(a,b,c):return min(a[0],b[0])-EPS<=c[0]<=max(a[0],b[0])+EPS and min(a[1],b[1])-EPS<=c[1]<=max(a[1],b[1])+EPS
    def intersects(a,b,c,d):
        x,y,z,w=cross(a,b,c),cross(a,b,d),cross(c,d,a),cross(c,d,b)
        return ((x>EPS and y<-EPS or x<-EPS and y>EPS) and (z>EPS and w<-EPS or z<-EPS and w>EPS)
            or abs(x)<=EPS and on(a,b,c) or abs(y)<=EPS and on(a,b,d)
            or abs(z)<=EPS and on(c,d,a) or abs(w)<=EPS and on(c,d,b))
    n=len(q)
    for i in range(n):
        if abs(cross(q[i-1],q[i],q[(i+1)%n]))<=EPS:raise ValueError('Polygon collinear/degenerate corner')
        for j in range(i+1,n):
            if j==i+1 or i==0 and j==n-1:continue
            if intersects(q[i],q[(i+1)%n],q[j],q[(j+1)%n]):raise ValueError('Polygon self-intersection or touching edges')
    area=sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(q,q[1:]+q[:1]))
    if abs(area)<=EPS:raise ValueError('Polygon degenerate projected area')
    sign=1 if area>0 else -1;remaining=list(range(n));triangles=[]
    while len(remaining)>3:
        for pos,b in enumerate(remaining):
            a=remaining[pos-1];c=remaining[(pos+1)%len(remaining)]
            if sign*cross(q[a],q[b],q[c])<=EPS:continue
            if any(all(sign*cross(q[x],q[y],q[other])>=-EPS for x,y in ((a,b),(b,c),(c,a)))
                for other in remaining if other not in (a,b,c)):continue
            triangles.append((a,b,c));del remaining[pos];break
        else:raise ValueError('Polygon ambiguous or ill-conditioned ear clipping')
    if sign*cross(*(q[index] for index in remaining))<=EPS:raise ValueError('Polygon degenerate final triangle')
    triangles.append(tuple(remaining))
    filled=sum(abs(cross(q[a],q[b],q[c])) for a,b,c in triangles)
    if abs(filled-abs(area))>1e-8*abs(area)+EPS:raise ValueError('Polygon triangulation area mismatch')
    return [tuple(ring[index] for index in triangle) for triangle in triangles]
