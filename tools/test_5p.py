import hou,json,math,collections
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'outputs';RULES=OUT/'YFS_DG_RULES';HIP=OUT/'YFS_DG_5P_ATOM_COMPAT_v1.hip'
hou.hipFile.load(str(HIP),suppress_save_prompt=True,ignore_load_warnings=False)
o=hou.node('/obj/YFS_DG_RULE_SYSTEM');a=o.node('YFS_DG_ASSEMBLY')
t=json.loads((RULES/'YFS_DG_5P_ASSEMBLY_v1.json').read_text(encoding='utf-8'));F=t['F_m'];RID=t['recipe_id']
assert a.evalParm('recipe_id')==RID
assert RID in a.parm('recipe_id').menuItems()
assert RID in o.parm('recipe_id').menuItems()
def geo(name):
    n=o.node(name);n.cook(force=True);assert not n.errors(),n.errors();return n.geometry()
qa={'recipe_id':RID,'scope':'User-approved PROJECT_5P_GENERIC; focused assembly checks only','tests':{}}
fixed=geo('OUT_5P_FIXED_ATOMS');full=geo('OUT_5P_FULL_PROJECT');assert len(fixed.prims())==41 and len(full.prims())==42
assert len(geo('VIEWPORT_OUTPUT').prims())==42
counts=collections.Counter(p.attribValue('asset_id') for p in fixed.prims());assert len(counts)==13 and counts['DG_LUDOU_A']==1 and counts['DG_GUAZI_GONG_A']==2
sharing={}
for p in fixed.prims():
    assert p.type()==hou.primType.PackedGeometry
    sharing.setdefault(p.attribValue('asset_id'),set()).add(str(p.intrinsicValue('geometryid')))
assert all(len(v)==1 for v in sharing.values())
qa['tests']['TEST_1_COMPLETENESS']={'status':'PASS','fixed_atoms':41,'generated_ang':1,'total_packed':42,'unique_fixed_atoms':13,'shared_geometry_per_atom':{k:len(v) for k,v in sharing.items()},'atom_counts':dict(counts)}
byid={p.attribValue('instance_id'):p for p in fixed.prims()};maxerr=0.
for i in t['instances']:
    p=byid[i['instance_id']];pos=p.points()[0].position();expected=hou.Vector3(tuple(x*F for x in i['P_F']));maxerr=max(maxerr,(pos-expected).length())
    matrix=hou.Matrix4(p.intrinsicValue('packedfulltransform'));assert abs(matrix.determinant()-1)<1e-6
    assert p.attribValue('z_rule_status')=='PROJECT_DERIVED' and p.attribValue('source_class')=='PROJECT_DERIVED'
assert maxerr<1e-6
qa['tests']['TEST_2_TEMPLATE_LAYERS']={'status':'PASS','max_placement_error_m':maxerr,'vertical_layers_F':t['vertical_layers_F'],'all_scales_unit':True,'shuatuo_historical_exact_length':byid['SHUATOU'].attribValue('historical_exact_length')}
connectors={p.attribValue('connector_id'):list(p.position()) for p in geo('OUT_5P_CONNECTORS').points()}
for c in t['expected_connectors']:assert math.dist(connectors[c['id']],c['position_m'])<1e-6
bb=full.boundingBox();fb=fixed.boundingBox()
assert abs(bb.maxvec()[2]-79*F)<1e-6 and abs(bb.minvec()[2])<1e-6
assert abs(connectors['CONN_WALL'][2]-75*F)<1e-6
assert abs(bb.maxvec()[2]-connectors['CONN_WALL'][2]-4*F)<1e-6
qa['tests']['TEST_3_CONNECTORS_BBOX']={'status':'PASS','connectors_m':connectors,'support_F':75,'bbox_top_reference_F':79,'full_preview_bbox_m':list(bb.sizevec()),'full_preview_bbox_min_m':list(bb.minvec()),'full_preview_bbox_max_m':list(bb.maxvec()),'fixed_atom_bbox_m':list(fb.sizevec()),'body_preview_extends_y_bbox':True}
ang=geo('OUT_GENERATED_ANG');assert len(ang.prims())==1
p=ang.points()[0];start=p.attribValue('anchor_start_P');end=p.attribValue('anchor_end_P')
assert abs(math.dist(start,end)/F-120)<1e-4
assert abs((start[2]-end[2])/(end[1]-start[1])-3/8)<1e-6
for k in ['bearing_top_inner','bearing_top_outer','bearing_bottom_inner','bearing_bottom_outer']:
    assert math.dist(p.attribValue(k+'_P'),[v*F for v in t['down_ang'][k+'_F']])<1e-6
assert math.dist(start,p.attribValue('bearing_top_inner_P'))>.1
assert not p.attribValue('connector_in') and not p.attribValue('connector_out')
assert p.attribValue('endpoint_status')=='UNRESOLVED_BEAM_INTERACTION'
assert ang.prims()[0].attribValue('endpoint_status')=='UNRESOLVED_BEAM_INTERACTION'
allparts=dict(byid,DOWN_ANG=ang.prims()[0]);pair_errors=[]
for pair in t['connector_pairings']:
    def world(i,point):
        if i=='ASSEMBLY':return hou.Vector3(point)
        return hou.Vector3(point)*hou.Matrix4(allparts[i].intrinsicValue('packedfulltransform'))
    pair_errors.append((world(pair['parent_instance'],pair['parent_local_P_m'])-world(pair['child_instance'],pair['child_local_P_m'])).length())
assert max(pair_errors)<1e-6
qa['tests']['TEST_3_CONNECTORS_BBOX'].update(project_pairings=len(pair_errors),max_project_pair_error_m=max(pair_errors))
pending=geo('OUT_UNRESOLVED');assert len(pending.points())==1 and pending.points()[0].attribValue('role')=='RIDING_BEAM_AND_ANG_TAIL'
qa['tests']['TEST_4_ANG_CONTROL_BODY_SEPARATION']={'status':'PASS','nominal_body_length_F':120,'generated_upper_line_length_F':math.dist(start,end)/F,'slope':3/8,'preview_start_F':[v/F for v in start],'preview_end_F':[v/F for v in end],'endpoint_status':p.attribValue('endpoint_status'),'preview_endpoints_are_connectors':False,'unresolved_interface':'RIDING_BEAM_AND_ANG_TAIL'}
# The full down-ang uses the existing generator; this is not an ANG topology re-test.
o.parm('generate_ang_preview').set(0);assert len(geo('VIEWPORT_OUTPUT').prims())==41;o.parm('generate_ang_preview').set(1)
switches=[]
for rid,expected in [('YFS_4P_EXT_COLUMNHEAD_STANDARD',21),('YFS_5P_EXT_COLUMNHEAD',0),('YFS_4P_EXT_INTER_INSERTED_ANG',1)]:
    o.parm('recipe_id').set(rid);vg=geo('VIEWPORT_OUTPUT');assert len(vg.prims())==expected
    assert len(geo('OUT_5P_FULL_PROJECT').prims())==0 and len(geo('OUT_5P_FIXED_ATOMS').prims())==0
    if rid=='YFS_4P_EXT_COLUMNHEAD_STANDARD':
        dims=vg.boundingBox().sizevec();assert max(abs(x-y) for x,y in zip(dims,[1.408,1.613333344,.850666642]))<1e-6
    if rid=='YFS_5P_EXT_COLUMNHEAD':
        assert len(geo('OUT_UNRESOLVED').points())==14
    switches.append({'recipe':rid,'viewport_primitives':expected,'5p_project_primitives':0})
o.parm('recipe_id').set(RID);assert len(geo('VIEWPORT_OUTPUT').prims())==42
o.parm('generate_5p_project').set(0);assert len(geo('VIEWPORT_OUTPUT').prims())==0;o.parm('generate_5p_project').set(1)
o.parm('show_debug_guides').set(1);geo('VIEWPORT_OUTPUT');o.parm('show_debug_guides').set(0)
qa['tests']['TEST_5_RECIPE_ISOLATION']={'status':'PASS','switches':switches,'return_to_5p':42,'full_toggle_off':0,'ang_toggle_off':41,'golden_4p_bbox_unchanged':True}
(OUT/'generated').mkdir(exist_ok=True);geo('OUT_5P_FULL_PROJECT').saveToFile(str(OUT/'generated/YFS_M_DG_5P_COLUMNHEAD_PROJECT.bgeo.sc'))
qa['status']='PASS';qa['limitations']=['Atom-compatible generic project variant, not a complete historical riding-beam reconstruction.','Down-ang body extension and flat end profile are project preview choices.','Connector pairing tests datum positions, not collision-free joinery or load bearing contact surfaces.']
hou.hipFile.save(str(HIP));hou.hipFile.clear(suppress_save_prompt=True);hou.hipFile.load(str(HIP),suppress_save_prompt=True,ignore_load_warnings=False)
o=hou.node('/obj/YFS_DG_RULE_SYSTEM');assert len(o.node('VIEWPORT_OUTPUT').geometry().prims())==42
qa['delivery_check']={'hip_reopened':True,'default_recipe':RID,'fixed_count':41,'ang_count':1,'debug_default':False}
(RULES/'ASSEMBLY_5P_QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
print(json.dumps(qa,ensure_ascii=False,indent=2),flush=True)
