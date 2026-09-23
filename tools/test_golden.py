import hou,json,math,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent; OUT=ROOT/'outputs'; RULES=OUT/'YFS_DG_RULES'; HIP=OUT/'YFS_DG_GOLDEN_4P_v1.hip'
hou.hipFile.load(str(HIP),suppress_save_prompt=True,ignore_load_warnings=False)
o=hou.node('/obj/YFS_DG_RULE_SYSTEM');a=o.node('YFS_DG_ASSEMBLY');gold=o.node('YFS_DG_GOLDEN_4P_ASSEMBLER')
t=json.loads((RULES/'YFS_DG_GOLDEN_4P_ASSEMBLY_v1.json').read_text(encoding='utf-8'))
qa={'scope':'Only Golden 4P tests 1-5; no atom topology, historical or ANG regression QA','tests':{}}
def geom(name):
 n=o.node(name);n.cook(force=True); assert not n.errors(),n.errors();return n.geometry()
g=geom('OUT_GOLDEN_4P_FULL');v=geom('VIEWPORT_OUTPUT')
assert len(g.prims())==21 and len(v.prims())==21
assert all(p.type()==hou.primType.PackedGeometry for p in g.prims())
sources={i['asset_id']:gold.node('ATOM_LIBRARY/'+i['asset_id']) for i in t['instances']}
assert all(n.type().name()=='usdimport' and n.evalParm('filepath1').endswith('/atoms/'+aid+'.usd') for aid,n in sources.items())
qa['tests']['TEST_1']={'status':'PASS','packed_instances':21,'visible_output_primitives':21,'all_sources':'Existing Atom Library USD files','display_node':o.displayNode().name()}
counts=dict(collections.Counter(p.attribValue('asset_id') for p in g.prims()))
assert counts['DG_LUDOU_A']==1 and len(counts)==12
ids=[p.attribValue('source_object') for p in g.prims()]
reference=json.loads((ROOT/'assets/atom_library/source/YFS_M_DG_4P_COLUMNHEAD_A.geometry-qa.json').read_text(encoding='utf-8'))
assert set(ids)==set(x['name'] for x in reference['objects'])
resolved=geom('OUT_VERTICAL_RESOLVED')
parts=[p for p in resolved.points() if p.attribValue('semantic_kind')=='PART_REQUEST']
assert len(parts)==21 and all(p.attribValue('z_rule_status')=='EXACT_GOLDEN' for p in parts)
# Count existing polygons after unpacking, without running geometry/topology QA.
unpack=o.createNode('unpack','TEMP_ACCEPTANCE_UNPACK');unpack.setInput(0,o.node('OUT_GOLDEN_4P_FULL'))
mesh=unpack.geometry(); print('UNPACK_TYPES',collections.Counter(str(p.type()) for p in mesh.prims()),flush=True)
tri=sum(max(0,len(p.vertices())-2) for p in mesh.prims()); assert tri==4380,tri
sharing={}
for p in g.prims():
 aid=p.attribValue('asset_id');sharing.setdefault(aid,set()).add(str(p.intrinsicValue('geometryid')))
assert all(len(s)==1 for s in sharing.values()),sharing
qa['tests']['TEST_2']={'status':'PASS','instances':len(ids),'unique_atoms':len(counts),'roles':counts,'source_object_set_matches':True,'equivalent_triangles':tri,'shared_geometry_per_atom':{k:len(v) for k,v in sharing.items()},'fixed_part_status':'EXACT_GOLDEN'}
bb=g.boundingBox(); actual=list(bb.sizevec()); err=[abs(x-y) for x,y in zip(actual,t['expected_bbox']['dimensions_m'])]
assert max(err)<.001 and abs(bb.minvec()[2])<1e-7
qa['tests']['TEST_3']={'status':'PASS','bbox_dimensions_m':actual,'bbox_min_m':list(bb.minvec()),'bbox_max_m':list(bb.maxvec()),'max_dimension_error_m':max(err),'tolerance_m':.001}
cgeo=geom('OUT_GOLDEN_4P_CONNECTORS'); connectors={p.attribValue('connector_id'):list(p.position()) for p in cgeo.points()}
assert len(connectors)==4
for c in t['expected_connectors']: assert math.dist(connectors[c['id']],c['position_m'])<1e-6
assert abs(connectors['CONN_WALL'][2]-.792)<1e-6 and abs(bb.maxvec()[2]-connectors['CONN_WALL'][2]-.058666667)<1e-6
byid={p.attribValue('instance_id'):p for p in g.prims()}
pair_errors=[]
for pair in t['connector_pairings']:
 def world(i,pos):
  if i=='ASSEMBLY':return hou.Vector3(pos)
  return hou.Vector3(pos)*hou.Matrix4(byid[i].intrinsicValue('packedfulltransform'))
 pair_errors.append((world(pair['parent_instance'],pair['parent_local_P_m'])-world(pair['child_instance'],pair['child_local_P_m'])).length())
assert max(pair_errors)<1e-6
qa['tests']['TEST_4']={'status':'PASS','connectors_m':connectors,'pair_count':len(pair_errors),'max_pair_error_m':max(pair_errors),'support_z_F':54,'bbox_top_F':58,'bbox_top_is_connector':False,'pair_scope':'Project template mating datums from preserved source placement'}
switches=[]
for rid in ['YFS_4P_EXT_INTER_INSERTED_ANG','YFS_5P_EXT_COLUMNHEAD']:
 a.parm('recipe_id').set(rid)
 gg=geom('OUT_GOLDEN_4P_FULL'); vv=geom('VIEWPORT_OUTPUT'); pending=geom('OUT_UNRESOLVED')
 assert len(gg.prims())==0
 assert not any(p.attribValue('asset_id')=='DG_LUDOU_A' for p in vv.prims()) if vv.findPrimAttrib('asset_id') else True
 assert not any(p.attribValue('z_rule_status')=='EXACT_GOLDEN' for p in pending.points())
 switches.append({'recipe':rid,'golden_instances':len(gg.prims()),'viewport_primitives':len(vv.prims()),'unresolved_requests':len(pending.points())})
a.parm('recipe_id').set(t['recipe_id']);assert len(geom('VIEWPORT_OUTPUT').prims())==21
o.parm('generate_full_golden_4p').set(0);assert len(geom('VIEWPORT_OUTPUT').prims())==0
o.parm('generate_full_golden_4p').set(1);assert len(geom('VIEWPORT_OUTPUT').prims())==21
o.parm('show_debug_guides').set(1);geom('VIEWPORT_OUTPUT');o.parm('show_debug_guides').set(0)
qa['tests']['TEST_5']={'status':'PASS','switches':switches,'return_to_golden_instances':21,'full_toggle_off_empty':True}
(OUT/'generated').mkdir(exist_ok=True)
(ROOT/'work').mkdir(exist_ok=True)
geom('OUT_GOLDEN_4P_FULL').saveToFile(str(OUT/'generated/YFS_M_DG_4P_COLUMNHEAD_GOLDEN.bgeo.sc'))
mesh=unpack.geometry();mesh.saveToFile(str(ROOT/'work/golden_for_visual.obj'))
qa['status']='PASS';qa['delivery_check']={'reopened_hip':True,'saved_recipe':t['recipe_id'],'show_debug_guides':False,'full_golden_default':True}
(RULES/'GOLDEN_4P_QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
unpack.destroy();hou.hipFile.save(str(HIP))
print(json.dumps(qa,ensure_ascii=False,indent=2),flush=True)
# Inspect available offscreen OpenGL renderer settings for a real-geometry visual check.
rop=hou.node('/out').createNode('opengl','TEMP_INSPECT_RENDER')
print('GLPARMS',[(p.name(),p.eval()) for p in rop.parms() if any(w in p.name() for w in ['camera','picture','res','object','light','back','shadow','ao','quality'])],flush=True)
