"""Embedded runtime: two HDAs, no external Python dependency, no BBox connectors."""
import json, math
from pathlib import Path
import hou

ANG_TYPES=('DOWN_ANG','INSERTED_ANG','UP_ANG','CORNER_ANG','INNER_CORNER_ANG','YOU_ANG')
VALID=('EXACT','DERIVED','PROJECT_MVP')
STRINGS=('ang_type preset_id z_source_class z_confidence anchor_start_id anchor_end_id connector_in connector_out '
 'anchor_status profile_style source_class confidence vertical_reason profile_json generator_status generator_reason '
 'nominal_lengths_json nominal_length_status length_relation generator_id ang_pin_metadata pivot_contract '
 'z_rule_status support_layer_token debug_kind request_id role semantic_kind').split()
FLOATS='z_F z_m width_F height_F tip_thickness_F nominal_length_F generated_length_m generated_plan_length_m'.split()
INTS='z_resolved anchors_resolved nominal_length_known anchor_start_valid anchor_end_valid'.split()

def detail(g,k,v):
 if not g.findGlobalAttrib(k): g.addAttrib(hou.attribType.Global,k,v)
 g.setGlobalAttribValue(k,v)

def schema(g):
 for k in STRINGS:
  if not g.findPointAttrib(k): g.addAttrib(hou.attribType.Point,k,'')
 for k in FLOATS:
  if not g.findPointAttrib(k): g.addAttrib(hou.attribType.Point,k,-1.)
 for k in INTS:
  if not g.findPointAttrib(k): g.addAttrib(hou.attribType.Point,k,0)
 for k in ('anchor_start_P','anchor_end_P','plan_guide_start_P','plan_guide_end_P','long_axis'):
  if not g.findPointAttrib(k): g.addAttrib(hou.attribType.Point,k,(0.,0.,0.))

def record(p):
 d={a.name():p.attribValue(a) for a in p.geometry().pointAttribs() if a.name()!='P'}
 d['P']=tuple(p.position())
 return d

def setpoint(p,d):
 p.setPosition(d['P'])
 for k,v in d.items():
  a=p.geometry().findPointAttrib(k)
  if k!='P' and a:
   if a.dataType()==hou.attribData.Float:
    v=tuple(float(x) for x in v) if isinstance(v,(list,tuple)) else float(v)
   p.setAttribValue(a,tuple(v) if isinstance(v,list) else v)

def clear(g):
 g.deletePrims(g.prims(),True)
 g.deletePoints(g.points())

def emit(g,d):
 p=g.createPoint(); setpoint(p,d); return p

def load(owner,parm,section):
 value=owner.evalParm(parm)
 path=Path(hou.expandString(value))
 if not path.is_file():
  # Default rule paths have embedded portable fallbacks; a custom typo is an error.
  raw=owner.parm(parm).unexpandedString()
  if raw != '$HIP/YFS_DG_RULES/'+section: raise hou.NodeError('Rule file not found: '+str(path))
  data=json.loads(owner.type().definition().sections()[section].contents())
 else:
  data=json.loads(path.read_text(encoding='utf-8-sig'))
 if data.get('profile_id')!='YFS_MVP01' or abs(data.get('F_m',0)-0.014666667)>1e-12:
  raise hou.NodeError('Unsupported profile or F unit in '+section)
 return data

def matches(d,match):
 return all(d.get(k)==v for k,v in match.items())

def is_ang(d):
 return d.get('role') in ANG_TYPES and d.get('semantic_kind')=='PART_REQUEST'

def recipe(g):
 if g.findGlobalAttrib('selected_recipe_json'): return json.loads(g.attribValue('selected_recipe_json'))
 return {}

def frame(d,records):
 # Reuse the Assembly branch direction and its authored plan origin. Never create a 45-degree rotation here.
 ref=d
 if d.get('branch')=='SHARED' and d.get('position')=='CORNER':
  ref=next((r for r in records if r.get('branch')=='CORNER' and r.get('semantic_kind')=='JUMP_ANCHOR'),d)
 direction=ref.get('branch_dir',(0.,0.,0.))
 length=math.hypot(direction[0],direction[1])
 if length<1e-12: return None
 u=(direction[0]/length,direction[1]/length,0.)
 dist=ref.get('distance_m',0.)
 origin=(ref['P'][0]-u[0]*dist,ref['P'][1]-u[1]*dist,0.)
 return origin,u

def world(local,fr,F):
 origin,u=fr; right=(u[1],-u[0],0.)
 return tuple(origin[k]+F*(right[k]*local[0]+u[k]*local[1]+(local[2] if k==2 else 0)) for k in range(3))

def solve(g,owner):
 rules=load(owner,'vertical_rule_file','YFS_DG_VERTICAL_RULES_v1.json'); F=rules['F_m']
 data=[record(p) for p in g.points()]
 for d in data:
  token=rules['aliases'].get(d.get('support_layer',''),d.get('support_layer',''))
  d.update(z_F=-1.,z_m=-1.,z_resolved=0,z_rule_status='UNRESOLVED',z_source_class='PROJECT_MVP',z_confidence='UNRESOLVED',
   support_layer_token=token,vertical_reason='No uniquely determined layer or mating rule.',anchor_start_id='',anchor_end_id='',
   anchor_start_P=(0.,0.,0.),anchor_end_P=(0.,0.,0.),anchors_resolved=0,anchor_start_valid=0,anchor_end_valid=0,
   anchor_status='UNRESOLVED',connector_in='',connector_out='',profile_json='',ang_type=d['role'] if is_ang(d) else '')
  if 'connector_status' in d: d['connector_status']='UNRESOLVED'
  chosen=None
  if token=='BASE': chosen=rules['base_references']['BASE']
  for l in rules['recipe_layers'].get(d.get('recipe_id'),[]):
   if l['layer_id']==token: chosen=l
  overrides=[x['layer'] for x in rules.get('authored_layer_rules',[]) if matches(d,x['match'])]
  if len(overrides)>1: raise hou.NodeError('Ambiguous authored layer rules for '+d.get('request_id',''))
  if overrides: chosen=overrides[0]
  if token=='BBOX_REFERENCE': chosen=None # Only a debug/reference datum, never a bearing request.
  if chosen and chosen['status'] in VALID and chosen.get('z_F') is not None:
   z=float(chosen['z_F'])
   d.update(z_F=z,z_m=z*F,z_resolved=1,z_rule_status=chosen['status'],z_source_class=chosen['source_class'],z_confidence=chosen['confidence'],vertical_reason=chosen['note'],P=(d['P'][0],d['P'][1],z*F))
   d['connector_in']='ASSEMBLY_BASE' if token=='BASE' else ''
   d['connector_out']='ASSEMBLY_UPPER_SUPPORT_4P' if token=='TOP_SUPPORT' and d.get('recipe_id')=='YFS_4P_EXT_COLUMNHEAD_STANDARD' else ''
   if 'connector_status' in d: d['connector_status']='ASSEMBLY_DATUM_ONLY'
  if is_ang(d):
   fr=frame(d,data)
   d['plan_guide_start_P']=fr[0] if fr else (d['P'][0],d['P'][1],0.)
   ref=next((r for r in data if r.get('branch')=='CORNER' and r.get('semantic_kind')=='JUMP_ANCHOR'),d) if d.get('branch')=='SHARED' else d
   d['plan_guide_end_P']=(ref['P'][0],ref['P'][1],0.)
   found=[a for a in rules['anchor_rules'] if matches(d,a['match'])]
   if len(found)>1: raise hou.NodeError('Ambiguous anchor rules for '+d.get('request_id',''))
   if found:
    a=found[0]
    if a['status'] in VALID and (a['frame']=='WORLD' or fr):
     if a['frame']=='WORLD': start,end=tuple(a['start_m']),tuple(a['end_m'])
     else: start,end=world(a['start_F'],fr,F),world(a['end_F'],fr,F)
     if not all(math.isfinite(x) for x in start+end) or math.dist(start,end)<1e-8: raise hou.NodeError('Invalid anchor rule '+a['rule_id'])
     prefix=d.get('request_id','')+'/'
     d.update(anchor_start_P=start,anchor_end_P=end,anchor_start_id=prefix+a['start_id'],anchor_end_id=prefix+a['end_id'],anchors_resolved=1,anchor_start_valid=1,anchor_end_valid=1,anchor_status=a['status'],
       z_F=start[2]/F,z_m=start[2],z_resolved=1,z_rule_status=a['status'],z_source_class=a['source_class'],z_confidence=a['confidence'],
       connector_in=prefix+a['start_id'],connector_out=prefix+a['end_id'],preset_id=a['preset_id'],profile_json=json.dumps(a['profile']),vertical_reason=a['note'],
       P=(d['P'][0],d['P'][1],start[2]))
     for key in ('width_F','height_F','tip_thickness_F','profile_style'): d[key]=a['profile'][key]
     if 'connector_status' in d: d['connector_status']='EXPLICIT_PROJECT_ANCHORS'
     if 'placement_status' in d: d['placement_status']='ANCHORS_RESOLVED_REQUEST_XY_RETAINED'
  # No solved assembly placement is claimed for fixed atoms without mating connectors.
  if d.get('production_source')=='ATOM' and 'placement_ready' in d: d['placement_ready']=0
 return data,rules

def cook_vertical(node):
 g=node.geometry(); owner=node.parent(); schema(g)
 data,rules=solve(g,owner)
 for p,d in zip(g.points(),data): setpoint(p,d)
 unresolved=sum(not d['z_resolved'] for d in data)
 detail(g,'vertical_unresolved_count',unresolved)
 detail(g,'vertical_rules_json',json.dumps(rules))
 detail(g,'vertical_contract','P.xy retained; anchor_start/end are authoritative ANG placement. Unknown Z uses validity flags.')
 detail(g,'bbox_top_is_connector',0)
 if owner.evalParm('strict') and unresolved: raise hou.NodeError(str(unresolved)+' unresolved vertical requests (Strict mode).')

def cook_vertical_filter(node,resolved):
 g=node.geometry(); g.deletePoints([p for p in g.points() if bool(p.attribValue('z_resolved'))!=resolved])

def cook_anchor_debug(node):
 g=node.geometry(); data=[record(p) for p in g.points()]; rules=json.loads(g.attribValue('vertical_rules_json')); clear(g)
 if not node.parent().evalParm('show_anchor_debug'): return
 for d in data:
  if d['anchors_resolved']:
   for name in ('start','end'):
    emit(g,dict(d,P=d['anchor_'+name+'_P'],debug_kind='RESOLVED_'+name.upper(),semantic_kind='ANCHOR_DEBUG'))
  elif d['z_resolved']:
   emit(g,dict(d,debug_kind='RESOLVED_LAYER',semantic_kind='LAYER_DEBUG'))
 rid=data[0].get('recipe_id') if data else ''
 for l in rules['recipe_layers'].get(rid,[]):
  if l['layer_id']=='BBOX_REFERENCE':
   emit(g,dict(P=(0.,0.,l['z_m']),recipe_id=rid,role='BBOX_REFERENCE',debug_kind='REFERENCE_NOT_CONNECTOR',z_F=float(l['z_F']),z_m=l['z_m'],z_rule_status=l['status'],connector_in='',connector_out='',semantic_kind='REFERENCE_DEBUG'))

def preset_for(d,b):
 pid=d.get('preset_id','')
 found=[p for p in b['presets'] if p['preset_id']==pid] if pid else [p for p in b['presets'] if p['ang_type']==d['ang_type']]
 if len(found)!=1 or found[0]['ang_type']!=d['ang_type']: return None
 return dict(found[0])

def evaluate(d,b,r):
 d=dict(d); p=preset_for(d,b)
 d.update(generator_status='UNRESOLVED',generator_reason='',nominal_length_F=-1.,nominal_length_known=0,nominal_length_status='UNRESOLVED',nominal_lengths_json='[]',length_relation='CONSTRAINT_NOT_BBOX',ang_pin_metadata='SEMANTIC_ONLY_NO_GEOMETRY')
 if not p: d['generator_reason']='Missing or incompatible preset'; return d
 d.update(preset_id=p['preset_id'],source_class=p['source_class'],confidence=p['confidence'])
 key=p.get('nominal_table'); nominal=[]
 if key!='EXTERIOR_INTERCOLUMN_DOWN_ANG' or (d.get('zone')=='EXTERIOR_EAVE' and d.get('position')=='INTERCOLUMN'):
  nominal=b['nominal_historical_body_lengths_F'].get(key,{}).get(str(r.get('puzuo')),[])
 d['nominal_lengths_json']=json.dumps(nominal)
 if len(nominal)==1 and nominal[0] is not None:
  d.update(nominal_length_F=float(nominal[0]),nominal_length_known=1,nominal_length_status='HISTORICAL_BODY_CONSTRAINT_ONLY')
 elif nominal: d['nominal_length_status']='LIST_ONLY_MEMBER_ASSIGNMENT_UNRESOLVED'
 if not p['enabled'] or p['geometry_mode']=='SCHEMA_ONLY': d['generator_reason']='Independent UP_ANG vertical/profile preset unresolved'; return d
 if not d.get('anchors_resolved') or d.get('z_rule_status') not in VALID or not d.get('anchor_start_id') or not d.get('anchor_end_id'):
  d['generator_reason']='Complete resolved Vertical Solver anchors required'; return d
 start,end=d['anchor_start_P'],d['anchor_end_P']; F=b['F_m']; run=math.hypot(end[0]-start[0],end[1]-start[1])/F
 if not all(math.isfinite(x) for x in start+end) or run<1e-5:
  d['generator_reason']='Invalid/vertical-only anchor axis'; return d
 supplied=json.loads(d.get('profile_json') or '{}')
 p.update(supplied)
 for k in ('width_F','height_F','tip_thickness_F','profile_style'):
  v=d.get(k)
  if (isinstance(v,(int,float)) and v>0) or (isinstance(v,str) and v): p[k]=v
 if any(not math.isfinite(p.get(k,0)) or p.get(k,0)<=0 for k in ('width_F','height_F','tip_thickness_F')):
  d['generator_reason']='Non-positive section'; return d
 if p['profile_style']!='PIZHU_BASIC': d['generator_reason']='Unsupported profile_style'; return d
 if d['ang_type']=='INSERTED_ANG':
  if abs(run-p['plan_length_F'])>1e-4 or abs((end[2]-start[2])/F+p['vertical_drop_F'])>1e-4:
   d['generator_reason']='Anchors disagree with approved inserted profile'; return d
 if d['ang_type']=='DOWN_ANG' and end[2]>=start[2]: d['generator_reason']='DOWN_ANG needs descending anchors'; return d
 d.update(profile_json=json.dumps(p),profile_style=p['profile_style'],width_F=float(p['width_F']),height_F=float(p['height_F']),tip_thickness_F=float(p['tip_thickness_F']),generator_status='RESOLVED',generator_reason='Complete anchors and explicit project profile',generated_length_m=math.dist(start,end),generated_plan_length_m=run*F)
 d['long_axis']=tuple((end[i]-start[i])/d['generated_length_m'] for i in range(3))
 return d

def cook_prepare(node):
 g=node.geometry(); schema(g); owner=node.parent(); b=load(owner,'preset_file','YFS_DG_ANG_PRESETS_v1.json'); r=recipe(g)
 data=[record(point) for point in g.points()]
 clear(g)
 for d in data:
  if not is_ang(d): continue
  d['ang_type']=d['role']; emit(g,evaluate(d,b,r))
 detail(g,'ang_presets_json',json.dumps(b))
 detail(g,'generated_length_definition','Distance between input anchors, NOT nominal historical body length or BBox.')

def control_geometry(d,F):
 p=json.loads(d['profile_json']); start,end=d['anchor_start_P'],d['anchor_end_P']
 L=math.hypot(end[0]-start[0],end[1]-start[1]); dz=end[2]-start[2]
 stations=[(0.,-p['height_F']*F,0.)]
 if d['ang_type']=='INSERTED_ANG': stations.append((p['head_start_F']*F,-p['height_F']*F,0.))
 stations.append((L,dz-p['tip_thickness_F']*F,dz))
 g=hou.Geometry(); rings=[]; w=p['width_F']*F/2
 for y,bottom,top in stations:
  ring=[]
  for pos in ((-w,y,bottom),(w,y,bottom),(w,y,top),(-w,y,top)):
   pt=g.createPoint(); pt.setPosition(pos); ring.append(pt)
  rings.append(ring)
 def face(points):
  f=g.createPolygon()
  for pt in points: f.addVertex(pt)
 face(rings[0])
 for a,c in zip(rings,rings[1:]):
  for i in range(4): face([a[i],c[i],c[(i+1)%4],a[(i+1)%4]])
 face(list(reversed(rings[-1])))
 return g

def verb(name,g,parms):
 v=hou.sopNodeTypeCategory().nodeVerb(name); v.setParms(parms); out=hou.Geometry(); v.execute(out,[g]); return out

def finished_geometry(d,F,bevel):
 g=control_geometry(d,F)
 if bevel>0:
  g=verb('polybevel::3.0',g,{'offset':bevel,'divisions':1,'ignoreflatedges':1,'ignoreflatpoints':1})
 # Preserve quads; split only polygons above four sides after bevel termination.
 g=verb('divide',g,{'convex':1,'usemaxsides':1,'numsides':4,'planar':1})
 return verb('normal',g,{'type':1,'cuspangle':60.})

def cook_mesh(node):
 g=node.geometry(); data=[record(p) for p in g.points()]; b=json.loads(g.attribValue('ang_presets_json')); clear(g)
 owner=node.parent(); bevel=owner.evalParm('bevel_width')
 if bevel<0: raise hou.NodeError('Bevel must be nonnegative')
 for d in data:
  if d['generator_status']!='RESOLVED': continue # Safety invariant even if UI option is disabled.
  if bevel>=min(d['width_F'],d['height_F'],d['tip_thickness_F'])*b['F_m']/2: raise hou.NodeError('Bevel exceeds half of the minimum section')
  mesh=finished_geometry(d,b['F_m'],bevel)
  start,end=d['anchor_start_P'],d['anchor_end_P']; dx,dy=end[0]-start[0],end[1]-start[1]; L=math.hypot(dx,dy); ux,uy=dx/L,dy/L
  # Geometry remains canonical (+Y plan, +Z up), only rigid rotation and translation on the pack.
  pt=g.createPoint(); pt.setPosition(start)
  packed=g.createPackedGeometry(mesh,pt)
  packed.setTransform(hou.Matrix4(hou.Matrix3(((uy,-ux,0.),(ux,uy,0.),(0.,0.,1.)))))
  d.update(P=start,generator_id='YFS_DG_ANG_GENERATOR',generator_status='GENERATED',pivot_contract='PACKED_LOCAL_ORIGIN_EQUALS_ANCHOR_START')
  setpoint(pt,d)
  for k in ('generator_id','ang_type','preset_id','nominal_length_F','generated_length_m','length_relation','source_class','confidence','request_id'):
   if not g.findPrimAttrib(k): g.addAttrib(hou.attribType.Prim,k,d[k])
   packed.setAttribValue(k,d[k])
 detail(g,'generated_ang_count',len(g.prims()))

def cook_pending(node):
 g=node.geometry(); g.deletePoints([p for p in g.points() if p.attribValue('generator_status')=='RESOLVED'])

def cook_guides(node):
 g=node.geometry(); data=[record(p) for p in g.points()]; clear(g)
 if not node.parent().evalParm('debug_guides'): return
 for d in data:
  known=d['anchors_resolved']
  a=d['anchor_start_P'] if known else d.get('plan_guide_start_P',d['P'])
  b=d['anchor_end_P'] if known else d.get('plan_guide_end_P',d['P'])
  label='RESOLVED_ANCHOR_GUIDE' if known else 'UNRESOLVED_PLAN_ONLY_Z_PLACEHOLDER'
  pts=[emit(g,dict(d,P=pos,debug_kind=label,semantic_kind='GUIDE')) for pos in (a,b)]
  if math.dist(a,b)>1e-8:
   line=g.createPolygon(is_closed=False)
   for pt in pts: line.addVertex(pt)
