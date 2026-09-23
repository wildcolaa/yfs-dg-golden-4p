import hou
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'outputs'
hou.hipFile.load(str(OUT/'YFS_DG_5P_ATOM_COMPAT_v1.hip'),suppress_save_prompt=True,ignore_load_warnings=False)
o=hou.node('/obj/YFS_DG_RULE_SYSTEM');cam=hou.node('/obj').createNode('cam','P5_PREVIEW_CAMERA')
eye=hou.Vector3((3.2,4.7,2.8));target=hou.Vector3((0,.22,.55));back=(eye-target).normalized();right=hou.Vector3((0,0,1)).cross(back).normalized();up=back.cross(right)
cam.setWorldTransform(hou.Matrix4(hou.Matrix3((tuple(right),tuple(up),tuple(back))))*hou.hmath.buildTranslate(eye))
cam.parm('projection').set('ortho');cam.parm('orthowidth').set(3.15)
rop=hou.node('/out').createNode('opengl','P5_PREVIEW_RENDER');rop.parm('camera').set(cam.path());rop.parm('picture').set(str(OUT/'5P_ATOM_COMPAT_PREVIEW.png'))
rop.parm('vobjects').set(o.path());rop.parm('tres').set(1);rop.parm('res1').set(1200);rop.parm('res2').set(1000)
rop.render();print('5P REAL GEOMETRY RENDER',rop.errors(),flush=True)
