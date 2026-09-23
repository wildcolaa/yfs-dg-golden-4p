"""User-authorized 5P project placement and preview metadata; no historical endpoint claims."""
import json,math
from pathlib import Path
import hou
P5_RECIPE='YFS_5P_EXT_COLUMNHEAD_GENERIC_ATOM_COMPAT'
P5_FILE='YFS_DG_5P_ASSEMBLY_v1.json'

def p5_template(owner):
    parm=owner.parm('assembly_template_file');raw=parm.getReferencedParm().unexpandedString();path=Path(parm.eval())
    if path.is_file():t=json.loads(path.read_text(encoding='utf-8-sig'))
    elif raw=='$HIP/YFS_DG_RULES/'+P5_FILE:t=json.loads(owner.type().definition().sections()[P5_FILE].contents())
    else:raise hou.NodeError('5P template not found: '+str(path))
    if t['recipe_id']!=P5_RECIPE:raise hou.NodeError('Wrong 5P template recipe')
    ids=[i['instance_id'] for i in t['instances']]
    if len(set(ids))!=len(ids):raise hou.NodeError('Duplicate template instance ID')
    for i in t['instances']:
        if i['scale']!=[1,1,1]:raise hou.NodeError('Only unit scale is allowed')
        if i['layer_id'] not in t['vertical_layers_F']:raise hou.NodeError('Unknown vertical layer')
        if len(i['orient'])!=4 or abs(sum(v*v for v in i['orient'])-1)>1e-6:raise hou.NodeError('Invalid orientation')
        if not all(math.isfinite(v) for v in i['P_F']+i['orient']+[t['vertical_layers_F'][i['layer_id']]]):raise hou.NodeError('Non-finite placement')
    return t

def p5_detail(g,k,v):
    if not g.findGlobalAttrib(k):g.addAttrib(hou.attribType.Global,k,v)
    g.setGlobalAttribValue(k,v)

def p5_schema(g):
    for k in 'instance_id layer_id template_id source_object validation_scope reuse_status reuse_class endpoint_status preview_endpoint_status tail_condition tip_profile bearing_segment_role connector_id historical_exact_length'.split():
        if not g.findPointAttrib(k):g.addAttrib(hou.attribType.Point,k,'')
    for k in ['bearing_top_inner_P','bearing_top_outer_P','bearing_bottom_inner_P','bearing_bottom_outer_P']:
        if not g.findPointAttrib(k):g.addAttrib(hou.attribType.Point,k,(0.,0.,0.))
    if not g.findPointAttrib('nominal_body_length_F'):g.addAttrib(hou.attribType.Point,'nominal_body_length_F',-1.)

def p5_emit(g,d):
    p=g.createPoint();p.setPosition(d.get('P',(0,0,0)))
    for k,v in d.items():
        a=g.findPointAttrib(k)
        if k=='P' or not a:continue
        if a.dataType()==hou.attribData.Float:v=tuple(float(x) for x in v) if isinstance(v,(list,tuple)) else float(v)
        p.setAttribValue(k,tuple(v) if isinstance(v,list) else v)
    return p

def p5_solve(node):
    g=node.geometry()
    if not g.findGlobalAttrib('recipe_id') or g.attribValue('recipe_id')!=P5_RECIPE:return
    t=p5_template(node.parent());F=t['F_m'];p5_schema(g);g.deletePoints(g.points())
    common=dict(recipe_id=P5_RECIPE,template_id=t['template_id'],zone='EXTERIOR_EAVE',position='COLUMNHEAD',enabled=1,
      orient=(0.,0.,0.,1.),scale=(1.,1.,1.),source_class='PROJECT_DERIVED',confidence='HIGH',z_source_class='PROJECT_DERIVED',z_confidence='HIGH',
      validation_scope='PROJECT_5P_GENERIC',z_rule_status='PROJECT_DERIVED',z_resolved=1,placement_ready=1,placement_status='PROJECT_DERIVED',
      connector_status='PROJECT_MATING_DATUM',generator_id='',preview_only=0,missing_atom=0,status='AVAILABLE')
    for i in t['instances']:
        z=t['vertical_layers_F'][i['layer_id']];pos=(i['P_F'][0]*F,i['P_F'][1]*F,z*F)
        d=dict(common);d.update(i);d.update(P=pos,semantic_kind='PART_REQUEST',production_source='ATOM',
          request_id=P5_RECIPE+'/'+i['instance_id'],support_layer=i['layer_id'],support_layer_token=i['layer_id'],z_F=z,z_m=z*F,
          connector_in=i['instance_id']+'/PROJECT_SEAT',connector_out=i['instance_id']+'/PROJECT_SUPPORT',
          historical_exact_length='FALSE' if i.get('historical_exact_length') is False else 'NOT_CLAIMED',
          vertical_reason='User-authorized 5P template local XY + explicit project vertical layer')
        p5_emit(g,d)
    a=t['down_ang'];d=dict(common)
    d.update(instance_id='DOWN_ANG',role='DOWN_ANG',semantic_kind='PART_REQUEST',production_source='GENERATOR',generator_id='GEN_DOWN_ANG',
      branch='OUT',jump_type='DOWN_ANG',jump_index=2,request_id=P5_RECIPE+'/OUT/J2/DOWN_ANG',asset_id='',P=(0,60*F,48*F),
      z_rule_status='PROJECT_MVP',z_F=a['preview_start_F'][2],z_m=a['preview_start_F'][2]*F,preview_only=1,
      support_layer='ANG_BEARING_CONTROL_SEGMENT',support_layer_token='ANG_BEARING_CONTROL_SEGMENT',ang_type='DOWN_ANG',
      anchor_start_P=tuple(v*F for v in a['preview_start_F']),anchor_end_P=tuple(v*F for v in a['preview_end_F']),
      anchor_start_id='PROJECT_PREVIEW_TAIL_NOT_CONNECTOR',anchor_end_id='PROJECT_PREVIEW_TIP_NOT_CONNECTOR',
      anchors_resolved=1,anchor_start_valid=1,anchor_end_valid=1,anchor_status='PROJECT_PREVIEW_ONLY',
      connector_in='',connector_out='',connector_status='PREVIEW_ENDPOINTS_ARE_NOT_CONNECTORS',
      preset_id='DOWN_ANG_5P_ATOM_COMPAT_PREVIEW',width_F=a['width_F'],height_F=a['height_F'],tip_thickness_F=a['height_F'],
      profile_style='PIZHU_BASIC',profile_json='{}',nominal_body_length_F=a['nominal_body_length_F'],
      endpoint_status=a['endpoint_status'],preview_endpoint_status=a['preview_endpoint_status'],tail_condition=a['tail_condition'],tip_profile=a['tip_profile'],
      bearing_segment_role=a['bearing_segment_role'],vertical_reason='Explicit bearing segment; 120F symmetric body extension is project preview only')
    for k in ['bearing_top_inner','bearing_top_outer','bearing_bottom_inner','bearing_bottom_outer']:d[k+'_P']=tuple(v*F for v in a[k+'_F'])
    p5_emit(g,d)
    for c in t['expected_connectors']:
        d=dict(common,P=tuple(c['position_m']),semantic_kind='DATUM',role=c['id'],connector_id=c['id'],production_source='SEMANTIC',
          request_id=P5_RECIPE+'/'+c['id'],z_F=c['position_F'][2],z_m=c['position_m'][2],connector_out=c['id'],placement_ready=0)
        p5_emit(g,d)
    for interface in t['unresolved_interfaces']:
        d=dict(common,P=(0,0,0),semantic_kind='INTERFACE_REQUEST',role=interface['interface_id'],request_id=P5_RECIPE+'/'+interface['interface_id'],
          production_source='SEMANTIC',z_resolved=0,z_rule_status='UNRESOLVED',z_F=-1.,z_m=-1.,placement_ready=0,
          status='UNRESOLVED',endpoint_status=interface['status'],vertical_reason=interface['reason'])
        p5_emit(g,d)
    p5_detail(g,'assembly_template_json',json.dumps(t));p5_detail(g,'assembly_validation_scope','PROJECT_5P_GENERIC')
    p5_detail(g,'historical_reconstruction_complete',0);p5_detail(g,'fixed_instance_count',len(t['instances']))

def p5_pack(node):
    g=node.geometry();owner=node.parent();rid=g.attribValue('recipe_id') if g.findGlobalAttrib('recipe_id') else ''
    records=[{a.name():p.attribValue(a) for a in g.pointAttribs()} for p in g.points()]
    g.deletePrims(g.prims(),True);g.deletePoints(g.points())
    if rid!=P5_RECIPE or not owner.evalParm('enabled'):return
    t=p5_template(owner);fixed={r['instance_id']:r for r in records if r.get('production_source')=='ATOM' and r.get('placement_ready')}
    if set(fixed)!=set(i['instance_id'] for i in t['instances']):raise hou.NodeError('Incomplete resolved 5P atom input')
    cache={}
    for i in t['instances']:
        r=fixed[i['instance_id']];aid=r['asset_id']
        if aid not in cache:
            n=owner.node('ATOM_LIBRARY/'+aid)
            if n is None:raise hou.NodeError('Missing Atom '+aid)
            mesh=n.geometry()
            if n.errors() or not mesh.prims():raise hou.NodeError('Unable to read Atom '+aid)
            proto=hou.Geometry();proto.createPackedGeometry(mesh);cache[aid]=proto.freeze()
        g.merge(cache[aid]);packed=g.prims()[-1];point=packed.points()[0]
        packed.setTransform(hou.Matrix4(hou.Quaternion(r['orient']).extractRotationMatrix3()));point.setPosition(r['P'])
        for k,v in r.items():
            if k!='P' and g.findPointAttrib(k):point.setAttribValue(k,v)
        for k in ['recipe_id','instance_id','asset_id','role','layer_id','branch','z_rule_status','source_class','confidence','reuse_status','reuse_class','validation_scope','historical_exact_length']:
            if not g.findPrimAttrib(k):g.addAttrib(hou.attribType.Prim,k,'')
            packed.setAttribValue(k,r.get(k,''))
    p5_detail(g,'fixed_packed_count',len(g.prims()));p5_detail(g,'unique_atom_count',len(cache))
    p5_detail(g,'support_z_m',t['expected_support_z_m']);p5_detail(g,'bbox_top_is_connector',0)

def p5_connectors(node):
    g=node.geometry();g.deletePrims(g.prims(),False)
    if not g.findGlobalAttrib('recipe_id') or g.attribValue('recipe_id')!=P5_RECIPE:g.deletePoints(g.points());return
    g.deletePoints([p for p in g.points() if p.attribValue('semantic_kind')!='DATUM'])

def p5_debug(node):
    g=node.geometry()
    if not g.findGlobalAttrib('recipe_id') or g.attribValue('recipe_id')!=P5_RECIPE:return
    p5_schema(g);t=p5_template(node.parent());F=t['F_m']
    for p in g.points():
        if p.attribValue('role')=='DOWN_ANG':p.setAttribValue('debug_kind','PROJECT_BODY_ENDPOINT_NOT_CONNECTOR')
    for k in ['bearing_top_inner','bearing_top_outer','bearing_bottom_inner','bearing_bottom_outer']:
        p5_emit(g,dict(P=tuple(v*F for v in t['down_ang'][k+'_F']),recipe_id=P5_RECIPE,role=k.upper(),semantic_kind='ANCHOR_DEBUG',
          debug_kind='PROJECT_BEARING_CONTROL',z_rule_status='PROJECT_DERIVED',bearing_segment_role='ANG_BEARING_CONTROL_SEGMENT'))

def p5_tag_generated(node):
    g=node.geometry()
    if not g.findGlobalAttrib('recipe_id') or g.attribValue('recipe_id')!=P5_RECIPE:return
    for prim in g.prims():
        p=prim.points()[0]
        for k in ['recipe_id','instance_id','endpoint_status','preview_endpoint_status','tail_condition','tip_profile','bearing_segment_role','validation_scope','connector_in','connector_out']:
            if not g.findPrimAttrib(k):g.addAttrib(hou.attribType.Prim,k,'')
            prim.setAttribValue(k,p.attribValue(k))
    p5_detail(g,'generated_length_definition','Project body preview = 120F along upper line; bearing segment separate; historical endpoints UNRESOLVED_BEAM_INTERACTION.')
