import json, hashlib
from pathlib import Path
from pxr import Usd, UsdGeom
ROOT=Path(__file__).resolve().parent.parent
LIB=ROOT/'assets/atom_library'
F=.22/15
manifest=json.loads((LIB/'YFS_DG_ATOM_LIBRARY.json').read_text(encoding='utf-8'))
meta=json.loads((LIB/'source/YFS_M_DG_4P_COLUMNHEAD_A.metadata.json').read_text(encoding='utf-8'))
atoms={a['asset_id']:a for a in manifest['atoms'][:12]}

def end_seat_center(aid):
    stage=Usd.Stage.Open(str(LIB/atoms[aid]['files']['usd']))
    mesh=next(UsdGeom.Mesh(p) for p in stage.Traverse() if p.IsA(UsdGeom.Mesh))
    points=mesh.GetPointsAttr().Get(); z=max(p[2] for p in points)
    xs=[p[0] for p in points if abs(p[2]-z)<1e-6 and p[0]>0]
    return round((min(xs)+max(xs))/2/F,5)*F

wall_x=end_seat_center('DG_MAN_GONG_A'); branch_x=end_seat_center('DG_LING_GONG_A')
instances=[]
for aid,a in atoms.items():
    for source in a['source_objects']:
        iid=source.removeprefix('YFS_M_DG_4P_COLUMNHEAD_A_')
        pos=list(a['pivot']['source_assembly_position_m'])
        basis='Atom manifest source_assembly_position_m; canonical USD axes retained.'
        if aid=='DG_SANDOU_A':
            sign=-1 if iid.endswith('_L') else 1
            if 'L1' in iid: pos[0]=sign*abs(pos[0])
            else:
                ref=atoms['DG_QIXIN_DOU_L2_'+('WALL' if 'WALL' in iid else 'IN' if '_IN_' in iid else 'OUT')+'_A']
                pos=list(ref['pivot']['source_assembly_position_m'])
                pos[0]=sign*(wall_x if 'WALL' in iid else branch_x)
            basis='Source-object canonical mapping; source tier datum; paired +/-X centers of existing gong end bearing lands. No new mesh.'
        elif source!=a['source_object']:
            pos[1]=-pos[1]
            basis='Source-object canonical mapping; symmetric IN/OUT source seat at +/-30F; canonical axes retained.'
        z=round(pos[2]/F,5)
        branch='OUT' if '_OUT' in iid else 'IN' if '_IN' in iid else 'WALL' if 'WALL' in iid or aid in ['DG_NIDAO_GONG_A','DG_MAN_GONG_A','DG_QIXIN_DOU_A','DG_SANDOU_A'] else 'SHARED'
        instances.append(dict(instance_id=iid,asset_id=aid,role=a['atom_type'],P_m=pos,orient=[0.,0.,0.,1.],scale=[1,1,1],
          layer_id='GOLDEN_Z_'+str(int(round(z)))+'F',branch=branch,source_object=source,part_z_F=z,transform_basis=basis))
lookup={i['instance_id']:i for i in instances}
pairings=[]
for i in instances:
    iid=i['instance_id']
    if iid=='LUDOU': parent='ASSEMBLY'; target=[0,0,0]
    elif iid in ['NIDAO','HUAGONG']: parent='LUDOU'
    elif iid=='QIXIN_L1' or iid.startswith('JIAOHU'): parent='HUAGONG'
    elif iid.startswith('SANDOU_L1'): parent='NIDAO'
    elif iid=='MANGONG' or iid=='SHUATOU': parent='QIXIN_L1'
    elif iid.startswith('LINGGONG'): parent='JIAOHU_'+i['branch']
    else: parent='MANGONG' if i['branch']=='WALL' else 'LINGGONG_'+i['branch']
    pp=lookup[parent]['P_m'] if parent!='ASSEMBLY' else [0,0,0]
    pairings.append(dict(parent_instance=parent,parent_connector='SEAT_FOR_'+iid,parent_local_P_m=[i['P_m'][k]-pp[k] for k in range(3)],
       child_instance=iid,child_connector=iid+'/SEAT',child_local_P_m=[0,0,0],tolerance_m=.001,
       basis='Project mating datum derived from source tier and preserved bearing geometry; not a new historical rule.'))
data=dict(schema_version='1.0.0',template_id='GOLDEN_4P_ASSEMBLY_TEMPLATE',recipe_id='YFS_4P_EXT_COLUMNHEAD_STANDARD',
 source_asset_id=meta['asset_id'],profile_id='YFS_MVP01',F_m=F,coordinate_system=meta['coordinate_system'],
 expected_bbox=dict(dimensions_m=[meta['dimensions_m'][k] for k in 'xyz'],min_m=[-.704,-.8066666666667,0],max_m=[.704,.8066666666667,58*F],tolerance_m=.001),
 expected_support_z_F=54,expected_support_z_m=.792,expected_bbox_top_F=58,expected_connectors=meta['connectors'],
 expected_instance_count=21,expected_unique_atom_count=12,expected_equivalent_triangles=4380,
 authority=dict(complete_instance_transform_table_found=False,canonical_source_mapping='YFS_DG_ATOM_LIBRARY.json / atoms[].source_objects',
 representative_transforms='atoms[].pivot.source_assembly_position_m',derivation='Only missing repeated placements: symmetric pairs and existing gong end-bearing centers.',
 derived_wall_sandou_abs_x_F=wall_x/F,derived_in_out_sandou_abs_x_F=branch_x/F,
 sources_sha256={str(p.relative_to(LIB)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [LIB/'YFS_DG_ATOM_LIBRARY.json',LIB/'source/YFS_M_DG_4P_COLUMNHEAD_A.metadata.json']}),
 instances=instances,connector_pairings=pairings)
assert len(instances)==21 and len(lookup)==21
(ROOT/'outputs/YFS_DG_RULES/YFS_DG_GOLDEN_4P_ASSEMBLY_v1.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print('TEMPLATE',len(instances),'wall seat F',wall_x/F,'in/out seat F',branch_x/F,flush=True)
