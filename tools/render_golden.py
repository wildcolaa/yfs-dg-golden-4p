import hou,json
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'outputs'
hou.hipFile.load(str(OUT/'YFS_DG_GOLDEN_4P_v1.hip'),suppress_save_prompt=True,ignore_load_warnings=True)
o=hou.node('/obj/YFS_DG_RULE_SYSTEM')
cam=hou.node('/obj').createNode('cam','GOLDEN_4P_INSPECTION_CAMERA')
eye=hou.Vector3((2.7,-3.7,2.35));target=hou.Vector3((0,0,.42));back=(eye-target).normalized();right=hou.Vector3((0,0,1)).cross(back).normalized();up=back.cross(right)
cam.setWorldTransform(hou.Matrix4(hou.Matrix3((tuple(right),tuple(up),tuple(back))))*hou.hmath.buildTranslate(eye))
cam.parm('resx').set(1100);cam.parm('resy').set(950);cam.parm('projection').set('ortho');cam.parm('orthowidth').set(2.6)
rop=hou.node('/out').createNode('opengl','GOLDEN_4P_PREVIEW_RENDER')
rop.parm('camera').set(cam.path());rop.parm('picture').set(str(OUT/'GOLDEN_4P_PREVIEW.png'))
rop.parm('vobjects').set(o.path());rop.parm('tres').set(1);rop.parm('res1').set(1100);rop.parm('res2').set(950)
rop.render();print('RENDERED',rop.errors(),flush=True)
