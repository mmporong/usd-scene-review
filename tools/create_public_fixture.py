"""Generate project-authored, dependency-free public USDA rack examples."""
from pathlib import Path


def scene(offset):
    lines = ['#usda 1.0','(', '    defaultPrim = "World"', '    metersPerUnit = 1',
             '    upAxis = "Z"', ')', 'def Xform "World" {']
    def cube(name, translate, scale, color):
        lines.extend(['        def Cube "'+name+'" {','            double size = 2',
            '            double3 xformOp:translate = '+str(tuple(translate)),
            '            double3 xformOp:scale = '+str(tuple(scale)),
            '            uniform token[] xformOpOrder = ["xformOp:translate", "xformOp:scale"]',
            '            color3f[] primvars:displayColor = ['+str(tuple(color))+']','        }'])
    cube('Floor',(0,0,-.08),(3,2,.08),(.68,.7,.72))
    lines.extend(['    def Xform "Rack" {','        double3 xformOp:translate = (0, '+str(offset)+', 0)',
                  '        uniform token[] xformOpOrder = ["xformOp:translate"]'])
    for i,(x,y) in enumerate([(-1,-.45),(1,-.45),(-1,.45),(1,.45)]):
        cube('Post'+str(i),(x,y,1.1),(.045,.045,1.1),(.35,.42,.46))
    for row,z in enumerate((.3,1.0,1.7)):
        cube('Shelf'+str(row),(0,0,z),(1.05,.5,.04),(.4,.48,.51))
        for column,x in enumerate((-.72,-.24,.24,.72)):
            color = (.08,.32,.52) if (row+column)%2==0 else (.82,.43,.08)
            cube('Bin'+str(row)+'_'+str(column),(x,0,z+.23),(.18,.3,.18),color)
    lines.extend(['    }','}'])
    return '\n'.join(lines)+'\n'


def generate(destination):
    destination = Path(destination)
    destination.mkdir(parents=True,exist_ok=True)
    for name,offset in [('before.usda',.2),('after.usda',0)]:
        (destination/name).write_text(scene(offset),encoding='utf-8')


if __name__=='__main__':
    generate(Path(__file__).resolve().parents[1]/'distribution/examples/synthetic')
