"""Reference-free lighting authored only in an owned anonymous session."""
from pxr import Usd, UsdLux


def prepare_lighting(stage, *, normalized=False):
    session = stage.GetSessionLayer()
    if not session.anonymous:
        raise ValueError('Review lighting requires an anonymous session')
    lights=[prim for prim in stage.Traverse() if UsdLux.LightAPI(prim)]
    if lights and not normalized:
        return {'label':'Source lights (review exposure)','source_light_count':len(lights)}
    if normalized:
        with Usd.EditContext(stage,session):
            for prim in lights:UsdLux.LightAPI(prim).CreateIntensityAttr(0)
    parent = stage.GetPseudoRoot() if normalized else (stage.GetDefaultPrim() or stage.GetPseudoRoot())
    path = parent.GetPath().AppendChild('_UsdSceneReviewLight')
    while stage.GetPrimAtPath(path):
        path = path.GetParentPath().AppendChild(path.name + '_')
    with Usd.EditContext(stage, session):
        light=UsdLux.DomeLight.Define(stage, path)
        light.CreateIntensityAttr(1000)
        light.CreateColorAttr((1,1,1))
        light.CreateExposureAttr(0)
    return {'label':'NORMALIZED fixed white dome; source visibility/materials retained' if normalized else 'Fallback white dome (no source lights)',
            'source_light_count':len(lights),'intensity':1000,'exposure':0}
