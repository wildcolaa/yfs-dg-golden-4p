"""Golden 4P project template; no generalized historical placement rules."""
import hou, json, math
from pathlib import Path
GOLDEN_RECIPE='YFS_4P_EXT_COLUMNHEAD_STANDARD'
GOLDEN_FILE='YFS_DG_GOLDEN_4P_ASSEMBLY_v1.json'

def golden_template(owner):
    raw=owner.parm('golden_template_file').getReferencedParm().unexpandedString()
    path=Path(owner.evalParm('golden_template_file'))
    if path.is_file(): data=json.loads(path.read_text(encoding='utf-8-sig'))
    elif raw=='$HIP/YFS_DG_RULES/'+GOLDEN_FILE:
        data=json.loads(owner.type().definition().sections()[GOLDEN_FILE].contents())
    else: raise hou.NodeError('Golden template not found: '+str(path))
    if data['recipe_id']!=GOLDEN_RECIPE: raise hou.NodeError('Wrong Golden recipe')
    for i in data['instances']:
        if i['scale']!=[1,1,1]: raise hou.NodeError('Golden requires unit scale')
        if not all(math.isfinite(v) for v in i['P_m']+i['orient']): raise hou.NodeError('Invalid Golden transform')
        if abs(sum(x*x for x in i['orient'])-1)>1e-6: raise hou.NodeError('Invalid Golden orientation')
    return data

def golden_attrib(g,kind,k,v):
    a=g.findPointAttrib(k) if kind==hou.attribType.Point else g.findPrimAttrib(k)
    if not a: g.addAttrib(kind,k,v)

def golden_detail(g,k,v):
    if not g.findGlobalAttrib(k): g.addAttrib(hou.attribType.Global,k,v)
    g.setGlobalAttribValue(k,v)

def golden_solve(node):
    g=node.geometry(); owner=node.parent()
    if not g.findGlobalAttrib('recipe_id') or g.attribValue('recipe_id')!=GOLDEN_RECIPE: return
    t=golden_template(owner)
    # Replace coarse assembly PART_REQUESTs, including the shared full-length Hua Gong.
    # Original semantic points remain available directly from Assembly output 0.
    g.deletePoints([p for p in g.points() if p.attribValue('semantic_kind')=='PART_REQUEST'])
    for k in ['instance_id','source_object','layer_id','template_id']:
        golden_attrib(g,hou.attribType.Point,k,'')
    for i in t['instances']:
        p=g.createPoint(); p.setPosition(i['P_m'])
        d=dict(i,recipe_id=GOLDEN_RECIPE,semantic_kind='PART_REQUEST',production_source='ATOM',
          request_id=GOLDEN_RECIPE+'/GOLDEN/'+i['instance_id'],support_layer=i['layer_id'],support_layer_token=i['layer_id'],
          z_rule_status='EXACT_GOLDEN',z_resolved=1,z_m=i['P_m'][2],z_F=i['P_m'][2]/t['F_m'],
          placement_ready=1,placement_status='EXACT_GOLDEN',connector_status='EXACT_GOLDEN_PROJECT_PAIR',
          z_source_class='SOURCE_ASSET_PROJECT_TEMPLATE',z_confidence='EXACT_GOLDEN',
          confidence='EXACT_GOLDEN',status='AVAILABLE',enabled=1,preview_only=0,missing_atom=0,
          generator_id='',zone='EXTERIOR_EAVE',position='COLUMNHEAD',template_id=t['template_id'],
          connector_in=i['instance_id']+'/SEAT',connector_out=i['instance_id']+'/SUPPORT',
          vertical_reason=i['transform_basis'])
        for k,v in d.items():
            a=g.findPointAttrib(k)
            if a:
                if a.dataType()==hou.attribData.Float:
                    v=tuple(float(x) for x in v) if isinstance(v,(list,tuple)) else float(v)
                p.setAttribValue(k,tuple(v) if isinstance(v,list) else v)
    golden_detail(g,'golden_template_json',json.dumps(t))
    golden_detail(g,'golden_instance_count',len(t['instances']))
    golden_detail(g,'vertical_unresolved_count',sum(not p.attribValue('z_resolved') for p in g.points()))
    golden_detail(g,'vertical_contract','Golden fixed parts: exact project template; other recipes: existing solver rules.')

def golden_pack(node):
    g=node.geometry(); owner=node.parent()
    rid=g.attribValue('recipe_id') if g.findGlobalAttrib('recipe_id') else ''
    records=[{a.name():p.attribValue(a) for a in g.pointAttribs()} for p in g.points()]
    g.deletePrims(g.prims(),True); g.deletePoints(g.points())
    if rid!=GOLDEN_RECIPE or not owner.evalParm('enabled'): return
    t=golden_template(owner)
    exact={r['instance_id']:r for r in records if r.get('z_rule_status')=='EXACT_GOLDEN'}
    if set(exact)!=set(i['instance_id'] for i in t['instances']): raise hou.NodeError('Complete EXACT_GOLDEN solver input required')
    cache={}
    for i in t['instances']:
        r=exact[i['instance_id']]; aid=r['asset_id']
        if aid not in cache:
            source=owner.node('ATOM_LIBRARY/'+aid)
            if source is None: raise hou.NodeError('Missing Atom Resolver: '+aid)
            geom=source.geometry()
            if source.errors() or not geom.prims(): raise hou.NodeError('Cannot load Atom: '+aid)
            prototype=hou.Geometry()
            prototype.createPackedGeometry(geom)
            cache[aid]=prototype.freeze()
        g.merge(cache[aid])
        packed=g.prims()[-1]; p=packed.points()[0]
        packed.setTransform(hou.Matrix4(hou.Quaternion(r['orient']).extractRotationMatrix3()))
        p.setPosition(r['P'])
        for k,v in r.items():
            if k!='P' and g.findPointAttrib(k): p.setAttribValue(k,v)
        for k in ['instance_id','asset_id','role','source_object','layer_id','branch','z_rule_status']:
            golden_attrib(g,hou.attribType.Prim,k,''); packed.setAttribValue(k,r[k])
    golden_detail(g,'golden_packed_count',len(g.prims()))
    golden_detail(g,'golden_unique_atom_count',len(cache))
    golden_detail(g,'golden_connectors_json',json.dumps(t['expected_connectors']))
    golden_detail(g,'golden_pairings_json',json.dumps(t['connector_pairings']))
    golden_detail(g,'support_z_m',t['expected_support_z_m'])
    golden_detail(g,'bbox_top_is_connector',0)

def golden_connectors(node):
    g=node.geometry(); owner=node.parent()
    rid=g.attribValue('recipe_id') if g.findGlobalAttrib('recipe_id') else ''
    g.deletePrims(g.prims(),True); g.deletePoints(g.points())
    if rid!=GOLDEN_RECIPE or not owner.evalParm('enabled'): return
    golden_attrib(g,hou.attribType.Point,'connector_id','')
    t=golden_template(owner)
    for c in t['expected_connectors']:
        p=g.createPoint(); p.setPosition(c['position_m']); p.setAttribValue('connector_id',c['id'])
        p.setAttribValue('semantic_kind','ASSEMBLY_CONNECTOR')
        p.setAttribValue('z_rule_status','EXACT_GOLDEN')
