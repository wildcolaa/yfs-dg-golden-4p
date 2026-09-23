"""User-approved Atom-compatible 5P project data. No historical reclassification."""
import json, math, copy
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
RULES=ROOT/'outputs/YFS_DG_RULES'
RID='YFS_5P_EXT_COLUMNHEAD_GENERIC_ATOM_COMPAT'
F=.22/15
layers={'BASE':0,'MEMBER_L0':12,'DOU_L1':27,'MEMBER_L1':33,'DOU_L2':48,'MEMBER_L2':54,'DOU_L3':69,'TOP_SUPPORT':75,'BBOX_TOP_REF':79}
instances=[]
def add(i,atom,x,y,layer,parent='ASSEMBLY',**extra):
    pf=[x,y,layers[layer]]
    instances.append(dict(instance_id=i,asset_id='DG_'+atom+'_A',role=atom,P_F=pf,P_m=[v*F for v in pf],orient=[0.,0.,0.,1.],scale=[1,1,1],
      layer_id=layer,branch='OUT' if y>0 else 'IN' if y<0 else 'WALL',parent_instance=parent,
      source_class='PROJECT_DERIVED',confidence='HIGH',validation_scope='PROJECT_5P_GENERIC',**extra))
add('LUDOU','LUDOU',0,0,'BASE')
add('NIDAO','NIDAO_GONG',0,0,'MEMBER_L0','LUDOU');add('HUA_1','HUA_GONG',0,0,'MEMBER_L0','LUDOU')
add('QIXIN_L1','QIXIN_DOU',0,0,'DOU_L1','HUA_1')
for side,x in [('L',-25),('R',25)]:add('SANDOU_L1_'+side,'SANDOU',x,0,'DOU_L1','NIDAO')
for branch,y in [('IN',-30),('OUT',30)]:add('JIAOHU_'+branch+'_1','JIAOHU_DOU',0,y,'DOU_L1','HUA_1')
add('WALL_MAN','MAN_GONG',0,0,'MEMBER_L1','QIXIN_L1')
for branch,y in [('IN',-30),('OUT',30)]:add('GUAZI_'+branch,'GUAZI_GONG',0,y,'MEMBER_L1','JIAOHU_'+branch+'_1')
add('HUA_2_IN','HUA_GONG',0,-30,'MEMBER_L1','JIAOHU_IN_1')
add('WALL_QIXIN','QIXIN_DOU_L2_WALL',0,0,'DOU_L2','WALL_MAN',reuse_class='EXISTING_CUT_VARIANT')
for side,x in [('L',-40),('R',40)]:add('WALL_SANDOU_'+side,'SANDOU',x,0,'DOU_L2','WALL_MAN')
for branch,y in [('IN',-30),('OUT',30)]:
    add('QIXIN_'+branch+'_1','QIXIN_DOU',0,y,'DOU_L2','GUAZI_'+branch)
    for side,x in [('L',-25),('R',25)]:add('SANDOU_'+branch+'_1_'+side,'SANDOU',x,y,'DOU_L2','GUAZI_'+branch)
    add('JIAOHU_'+branch+'_2','JIAOHU_DOU',0,y*2,'DOU_L2','HUA_2_IN' if branch=='IN' else 'DOWN_ANG')
for branch,y in [('IN',-30),('OUT',30)]:
    add('MAN_'+branch,'MAN_GONG',0,y,'MEMBER_L2','QIXIN_'+branch+'_1')
    add('LING_'+branch,'LING_GONG',0,y*2,'MEMBER_L2','JIAOHU_'+branch+'_2')
add('SHUATOU','SHUATOU',0,0,'MEMBER_L2','WALL_QIXIN',reuse_status='PROJECT_ATOM_COMPAT',historical_exact_length=False)
for branch,y in [('IN',-30),('OUT',30)]:
    add('QIXIN_MAN_'+branch,'QIXIN_DOU',0,y,'DOU_L3','MAN_'+branch)
    for side,x in [('L',-40),('R',40)]:add('SANDOU_MAN_'+branch+'_'+side,'SANDOU',x,y,'DOU_L3','MAN_'+branch)
    add('QIXIN_LING_'+branch,'QIXIN_DOU_L2_'+branch,0,y*2,'DOU_L3','LING_'+branch,reuse_class='EXISTING_CUT_VARIANT')
    for side,x in [('L',-30),('R',30)]:add('SANDOU_LING_'+branch+'_'+side,'SANDOU',x,y*2,'DOU_L3','LING_'+branch)
add('QIXIN_TOP_WALL','QIXIN_DOU_L2_WALL',0,0,'DOU_L3','SHUATOU',reuse_class='EXISTING_CUT_VARIANT')
assert len(instances)==41
half_run=60/math.sqrt(1+(3/8)**2)
start=[0,45-half_run,53.625+half_run*3/8];end=[0,45+half_run,53.625-half_run*3/8]
ang=dict(instance_id='DOWN_ANG',type='DOWN_ANG',nominal_body_length_F=120,width_F=10,height_F=15,slope={'rise':3,'run':8},
 bearing_top_inner_F=[0,30,59.25],bearing_top_outer_F=[0,60,48],bearing_bottom_inner_F=[0,30,44.25],bearing_bottom_outer_F=[0,60,33],
 endpoint_status='UNRESOLVED_BEAM_INTERACTION',bearing_segment_role='ANG_BEARING_CONTROL_SEGMENT',
 preview_start_F=start,preview_end_F=end,preview_endpoint_policy='SYMMETRIC_ABOUT_BEARING_MIDPOINT',
 preview_length_measure='120F along upper control line, NOT 120F horizontal projection',
 preview_endpoint_status='PROJECT_PREVIEW_ONLY_NOT_CONNECTOR',tail_condition='UNRESOLVED_BEAM_INTERACTION',
 tip_profile='PROJECT_CONSTANT_SECTION_FLAT_END',historical_endpoint_connectors=False)
connectors=[dict(id=i,position_F=p,position_m=[v*F for v in p],source_class='PROJECT_DERIVED',confidence='HIGH') for i,p in [
 ('CONN_BOTTOM',[0,0,0]),('CONN_OUTBOARD',[0,60,75]),('CONN_INBOARD',[0,-60,75]),('CONN_WALL',[0,0,75])]]
lookup={i['instance_id']:i for i in instances};pairings=[]
for i in instances:
    parent=i['parent_instance'];pp=lookup[parent]['P_F'] if parent in lookup else start if parent=='DOWN_ANG' else [0,0,0]
    pairings.append(dict(parent_instance=parent,parent_local_P_m=[(i['P_F'][k]-pp[k])*F for k in range(3)],child_instance=i['instance_id'],child_local_P_m=[0,0,0],
      basis='User-approved project placement datum; DOWN_ANG target is bearing_top_outer, not mesh endpoint.',tolerance_m=.001))
t=dict(schema_version='1.0.0',template_id=RID,recipe_id=RID,profile_id='YFS_MVP01',F_m=F,puzuo=5,
 source_class='PROJECT_DERIVED_FROM_GOLDEN_4P',confidence='HIGH',historical_reconstruction_complete=False,
 specification_source='User-provided 5P Atom-compatible specification, 2026-09-24; citation placeholders are not independently verified sources.',
 reuse_policy='Existing canonical atoms; unit scale only; no new Blender atom or historical riding-beam reconstruction.',
 jump_sequence={'out':['CHAO','DOWN_ANG'],'in':['CHAO','CHAO']},jump_positions_F={'out_1':30,'out_2':60,'in_1':-30,'in_2':-60},
 vertical_layers_F=layers,expected_support_z_F=75,expected_support_z_m=75*F,bbox_top_reference_F=79,bbox_top_reference_m=79*F,
 expected_fixed_instances=41,expected_generated_ang=1,expected_unique_atoms=13,
 instances=instances,down_ang=ang,expected_connectors=connectors,connector_pairings=pairings,
 unresolved_interfaces=[dict(interface_id='RIDING_BEAM_AND_ANG_TAIL',status='UNRESOLVED_BEAM_INTERACTION',reason='Beam/tail relation and historical full-body endpoints remain unspecified.')])
def write(name,d):
    (RULES/name).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
write('YFS_DG_5P_ASSEMBLY_v1.json',t)
recipes=json.loads((RULES/'YFS_DG_RECIPES_v1.json').read_text(encoding='utf-8'))
r=copy.deepcopy(next(x for x in recipes['recipes'] if x['recipe_id']=='YFS_5P_EXT_COLUMNHEAD'))
r.update(recipe_id=RID,status='PROJECT_ATOM_COMPAT',confidence='HIGH',source_class='PROJECT_DERIVED',mesh_instancing_ready=True,
 assembly_template={'template_file':'YFS_DG_5P_ASSEMBLY_v1.json','stack_status':'PROJECT_DERIVED','double_gong_roles':[],'scope':'Fixed parts are expanded by the explicit 5P template, not by generic branch role expansion.'})
recipes['recipes'].append(r);write('YFS_DG_RECIPES_v2.json',recipes)
vertical=json.loads((RULES/'YFS_DG_VERTICAL_RULES_v1.json').read_text(encoding='utf-8'))
vertical['recipe_layers'][RID]=[dict(layer_id=('BBOX_REFERENCE' if k=='BBOX_TOP_REF' else k),z_F=v,z_m=v*F,status='DERIVED',source_class='PROJECT_DERIVED',confidence='HIGH',note='User-approved 5P Atom-compatible project layer; not PRIMARY_YFS.') for k,v in layers.items()]
vertical['assembly_template_files']={RID:'YFS_DG_5P_ASSEMBLY_v1.json'};write('YFS_DG_VERTICAL_RULES_v2.json',vertical)
presets=json.loads((RULES/'YFS_DG_ANG_PRESETS_v1.json').read_text(encoding='utf-8'))
p=copy.deepcopy(next(x for x in presets['presets'] if x['preset_id']=='DOWN_ANG_STANDARD'))
p.update(preset_id='DOWN_ANG_5P_ATOM_COMPAT_PREVIEW',source_class='PROJECT_DERIVED',confidence='HIGH',tip_thickness_F=15,
 nominal_table='USER_PROJECT_COLUMNHEAD_DOWN_ANG',station_policy='PROJECT_SYMMETRIC_NOMINAL_PREVIEW',nominal_length_usage='USER_SPECIFIED_120F_PREVIEW_NOT_HISTORICAL_ENDPOINTS',
 constraints=['10F width x 15F vertical height, 3/8 downward slope.', 'Bearing segment is separate from preview body endpoints.', 'Flat end constant-section preview; tail/beam relation unresolved.'])
presets['presets'].append(p);presets['nominal_historical_body_lengths_F']['USER_PROJECT_COLUMNHEAD_DOWN_ANG']={'5':[120]}
write('YFS_DG_ANG_PRESETS_v2.json',presets)
print('5P DATA',len(instances),'fixed + 1 ANG; preview endpoints F',start,end,flush=True)
