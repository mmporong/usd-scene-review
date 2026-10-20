"""Reference-free lighting authored only in an owned anonymous session."""
from pxr import Usd, UsdLux


def prepare_lighting(stage):
    session = stage.GetSessionLayer()
    if not session.anonymous:
        raise ValueError('Review lighting requires an anonymous session')
    if any(UsdLux.LightAPI(prim) for prim in stage.Traverse()):
        return
    parent = stage.GetDefaultPrim() or stage.GetPseudoRoot()
    path = parent.GetPath().AppendChild('_UsdSceneReviewLight')
    while stage.GetPrimAtPath(path):
        path = path.GetParentPath().AppendChild(path.name + '_')
    with Usd.EditContext(stage, session):
        UsdLux.DomeLight.Define(stage, path).CreateIntensityAttr(1000)
