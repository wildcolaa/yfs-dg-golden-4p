"""Shared semantic contract embedded in the three YFS HDA definitions.
No mesh generation, bounding-box inference, or vertical solving.
"""
import json
import math
from pathlib import Path
import hou

FILES = {'profile': 'YFS_DG_PROFILE_v1.json', 'atom_map': 'YFS_DG_ATOM_MAP_v1.json',
         'rules': 'YFS_DG_RULE_TABLE_v1.json', 'recipes': 'YFS_DG_RECIPES_v1.json'}
GOLDEN = 'YFS_4P_EXT_COLUMNHEAD_STANDARD'
DEFAULT_ROOT = 'C:/Users/鲸/Downloads/YFS_DG_ATOM_LIBRARY_V1_1'
BRANCH_ANGLES = {'OUT': 0, 'IN': 180, 'FRONT': 0, 'RETURN': 90, 'CORNER': 45}
STRINGS = ('recipe_id zone position branch jump_type heart_mode gong_stack role asset_id generator_id '
           'production_source support_layer z_rule_status source_class confidence request_id parent_jump_id '
           'semantic_kind connector_in connector_out mate_role status asset_path jump_json '
           'allowed_roles_json placement_status connector_status').split()
INTS = 'branch_index jump_index enabled missing_atom placement_ready datum_known preview_only'.split()
FLOATS = 'distance_F distance_m projection_F branch_angle_deg datum_z_F datum_z_m'.split()

def detail(g, name, value):
    if not g.findGlobalAttrib(name):
        g.addAttrib(hou.attribType.Global, name, value)
    g.setGlobalAttribValue(name, value)

def schema(g):
    for name in STRINGS:
        if not g.findPointAttrib(name): g.addAttrib(hou.attribType.Point, name, '')
    for name in INTS:
        if not g.findPointAttrib(name): g.addAttrib(hou.attribType.Point, name, 0)
    for name in FLOATS:
        if not g.findPointAttrib(name): g.addAttrib(hou.attribType.Point, name, 0.0)
    for name, value in [('branch_dir', (0., 1., 0.)), ('scale', (1., 1., 1.))]:
        if not g.findPointAttrib(name): g.addAttrib(hou.attribType.Point, name, value)
    if not g.findPointAttrib('orient'):
        verb = hou.sopNodeTypeCategory().nodeVerb('attribcreate::2.0')
        verb.setParms({'numattr': ({'name#': 'orient', 'enable#': 1, 'class#': 2, 'type#': 0,
                                   'typeinfo#': 6, 'size#': 4,
                                   'default#v': (0., 0., 0., 1.), 'writevalues#': 0},)})
        empty = hou.Geometry()
        verb.execute(empty, [])
        g.merge(empty)

def emit(g, data):
    p = g.createPoint()
    p.setPosition(data.get('P', (0., 0., 0.)))
    for k, v in data.items():
        if k != 'P' and g.findPointAttrib(k):
            p.setAttribValue(k, tuple(v) if isinstance(v, list) else v)
    return p

def record(p):
    d = {a.name(): p.attribValue(a) for a in p.geometry().pointAttribs() if a.name() != 'P'}
    d['P'] = tuple(p.position())
    return d

def base_record(r):
    return dict(recipe_id=r['recipe_id'], zone=r['zone'], position=r['position'],
                branch='SHARED', branch_index=-1, jump_index=0, enabled=1,
                production_source='SEMANTIC', semantic_kind='PART_REQUEST',
                support_layer='BASE', z_rule_status='UNRESOLVED',
                source_class=r.get('source_class', 'USER_CONFIRMED_RULES'),
                confidence=r.get('confidence', 'CONFIRMED_SEMANTIC'),
                status='UNRESOLVED', orient=(0., 0., 0., 1.),
                scale=(1., 1., 1.), placement_ready=0,
                placement_status='PLAN_DATUM_ONLY_Z_UNRESOLVED', connector_status='UNRESOLVED')

def load_bundle(owner):
    folder = Path(hou.expandString('$HIP/YFS_DG_RULES'))
    found = [(folder / name).is_file() for name in FILES.values()]
    if any(found) and not all(found):
        raise hou.NodeError('Incomplete YFS_DG_RULES: all four rule files are required')
    if all(found):
        return {k: json.loads((folder / n).read_text(encoding='utf-8-sig')) for k, n in FILES.items()}
    return json.loads(owner.type().definition().sections()['YFSBundle.json'].contents())

def choose(bundle, rid):
    matches = [r for r in bundle['recipes']['recipes'] if r['recipe_id'] == rid]
    if len(matches) != 1: raise hou.NodeError('Unknown or duplicate recipe_id: ' + rid)
    return matches[0]

def menu(kwargs):
    result = []
    for r in load_bundle(kwargs['node'])['recipes']['recipes']:
        result.extend([r['recipe_id'], r['recipe_id']])
    return result

def context(g, owner):
    bundle = json.loads(g.attribValue('yfs_bundle_json')) if g.findGlobalAttrib('yfs_bundle_json') else load_bundle(owner)
    inherited = g.attribValue('recipe_id') if g.findGlobalAttrib('recipe_id') else GOLDEN
    rid = owner.evalParm('recipe_id') if owner.parm('recipe_id') else ''
    r = choose(bundle, rid or inherited)
    root = owner.evalParm('atom_root') if owner.parm('atom_root') else ''
    if not root and g.findGlobalAttrib('atom_root'): root = g.attribValue('atom_root')
    root = root or hou.getenv('YFS_DG_ATOM_ROOT') or DEFAULT_ROOT
    return bundle, r, hou.expandString(root)

def write_context(g, b, r, root):
    values = dict(yfs_bundle_json=json.dumps(b), selected_recipe_json=json.dumps(r), recipe_id=r['recipe_id'],
                  profile_id='YFS_MVP01', F_m=float(b['profile']['F_m']), M_m=float(b['profile']['M_m']),
                  puzuo_out=0, puzuo_in=0, rule_version=1, rule_revision=1, atom_root=root,
                  status=r.get('status', 'SEMANTIC_READY'), mesh_instancing_ready=0,
                  golden_metadata_applicable=int(r['recipe_id'] == GOLDEN),
                  golden_support_local_z_F=54. if r['recipe_id'] == GOLDEN else -1.,
                  golden_bbox_top_F=58. if r['recipe_id'] == GOLDEN else -1.,
                  bbox_top_is_connector=0,
                  point_layout_contract='JUMP_ANCHOR + PART_REQUEST; plan Z=0 except explicit DATUM; no solved mesh assembly')
    for branch in r.get('branches', []):
        if branch['branch'] in ('OUT', 'IN'):
            values['puzuo_' + branch['branch'].lower()] = int(branch.get('effective_puzuo') or 0)
    for k, v in values.items(): detail(g, k, v)

def clear_points(g):
    g.deletePrims(g.prims(), True)
    g.deletePoints(g.points())

def cook_context(node):
    g, owner = node.geometry(), node.parent()
    b, r, root = context(g, owner)
    clear_points(g)
    write_context(g, b, r, root)
    schema(g)

def branch_angle(owner):
    name = owner.evalParm('branch')
    return BRANCH_ANGLES.get(name, 0.)

def cook_branch(node):
    g, owner = node.geometry(), node.parent()
    b, r, root = context(g, owner)
    origin = tuple(g.points()[0].position()) if g.points() else (0., 0., 0.)
    # Branch is a local plan skeleton: no incoming height is treated as bearing data.
    origin = (origin[0], origin[1], 0.)
    clear_points(g)
    write_context(g, b, r, root)
    schema(g)
    name = owner.evalParm('branch')
    if name not in BRANCH_ANGLES: raise hou.NodeError('Unsupported branch: ' + name)
    found = [(i, x) for i, x in enumerate(r.get('branches', [])) if x['branch'] == name]
    override = owner.evalParm('jump_sequence').strip()
    if not found and not override: return
    index, branch = found[0] if found else (0, {'jumps': []})
    jumps = json.loads(override) if override else branch['jumps']
    jumps = [dict(jump_type=j) if isinstance(j, str) else j for j in jumps]
    if r.get('system_type') == 'STANDARD_PUZUO' and not override:
        if len(jumps) != branch['effective_puzuo'] - 3: raise hou.NodeError('STANDARD_PUZUO branch count mismatch')
    if r['zone'] == 'INTERIOR_SLOT':
        if r.get('puzuo') not in (4, 5, 6, 7): raise hou.NodeError('INTERIOR_SLOT supports 4P-7P')
        if any(j['jump_type'] != 'CHAO' for j in jumps): raise hou.NodeError('INTERIOR_SLOT must be CHAO_ONLY')
    angle = owner.evalParm('branch_angle_deg')
    a = math.radians(angle)
    direction = (math.sin(a), math.cos(a), 0.)
    common = base_record(r)
    common.update(branch=name, branch_index=index, branch_angle_deg=angle, branch_dir=direction,
                  orient=(0., 0., -math.sin(a / 2), math.cos(a / 2)))
    if owner.evalParm('create_root_point'):
        d = dict(common, semantic_kind='ROOT', role='ROOT', P=origin, support_layer='BASE',
                 request_id=r['recipe_id'] + '/' + name + '/ROOT')
        emit(g, d)
    spacing = owner.evalParm('jump_spacing_F')
    if spacing <= 0: raise hou.NodeError('jump_spacing_F must be positive')
    for n, j in enumerate(jumps, 1):
        projection = n * spacing
        radial = projection * (math.sqrt(2.) if name == 'CORNER' else 1.)
        distance = radial * b['profile']['F_m']
        d = dict(common, semantic_kind='JUMP_ANCHOR', role='JUMP_ANCHOR', jump_index=n,
                 jump_type=j['jump_type'], heart_mode=j.get('heart_mode', 'COUNTED'),
                 gong_stack=j.get('gong_stack', 'DOUBLE'), distance_F=radial, distance_m=distance,
                 projection_F=projection, support_layer='LAYER_JUMP_' + str(n),
                 P=(origin[0] + direction[0] * distance, origin[1] + direction[1] * distance, 0.),
                 request_id=r['recipe_id'] + '/' + name + '/J' + str(n), jump_json=json.dumps(j))
        emit(g, d)
    detail(g, 'branch_origin', origin)

def resolve(d, role, b, root, generator=''):
    d.update(role=role, asset_id='', asset_path='', generator_id=generator, missing_atom=0,
             semantic_kind='PART_REQUEST', production_source='GENERATOR' if generator else 'ATOM')
    if generator:
        registry = {x['generator_id'] for x in b['rules']['generator_registry']}
        if generator not in registry: raise hou.NodeError('Unregistered generator: ' + generator)
        d.update(status='PLANNED', connector_status='UNRESOLVED')
    else:
        mapping = next((x for x in b['atom_map']['roles'] if x['role'] == role), {})
        aid = mapping.get('asset_id') or ''
        rel = mapping.get('files', {}).get('usd', '')
        available = bool(aid and rel and (Path(root) / rel).is_file())
        d.update(asset_id=aid, asset_path=str(Path(root) / rel).replace('\\', '/') if rel else '',
                 missing_atom=int(not available), status='AVAILABLE' if available else 'MISSING_ATOM')
    return d

def cook_jump(node):
    g, owner = node.geometry(), node.parent()
    b, r, root = context(g, owner)
    anchors = [record(p) for p in g.points() if p.attribValue('semantic_kind') == 'JUMP_ANCHOR']
    clear_points(g)
    write_context(g, b, r, root)
    schema(g)
    excluded = set(r.get('excluded_roles', []))
    allowed = b['rules']['gong_stack_semantic']['DOUBLE'].get('allowed_role_combinations', [])
    for anchor in anchors:
        j = json.loads(anchor['jump_json'])
        kind = anchor['jump_type']
        pairs = [('HUA_GONG', '')] if kind == 'CHAO' else [(kind, 'GEN_' + kind)]
        for role in j.get('required_roles', []):
            if role not in [x[0] for x in pairs] and role not in ('GUAZI_GONG', 'MAN_GONG'): pairs.append((role, ''))
        for gen in j.get('required_generators', []):
            if gen not in [x[1] for x in pairs]: pairs.append((gen.removeprefix('GEN_'), gen))
        counted = anchor['heart_mode'] == 'COUNTED'
        if counted:
            pairs.append(('COUNTED_TRANSVERSE_SUPPORT', 'GEN_COUNTED_TRANSVERSE_SUPPORT'))
            if anchor['gong_stack'] == 'DOUBLE':
                # Only explicitly assigned recipe/template roles are instantiated.
                roles = j.get('transverse_roles', r.get('assembly_template', {}).get('double_gong_roles', []))
                roles = list(dict.fromkeys(roles + [x for x in j.get('required_roles', []) if x in ('GUAZI_GONG', 'MAN_GONG')]))
                pairs.extend((role, '') for role in roles)
        elif anchor['heart_mode'] != 'STOLEN':
            raise hou.NodeError('Unknown heart_mode: ' + anchor['heart_mode'])
        for role, gen in dict.fromkeys(pairs):
            if role in excluded: continue
            if not counted and role in ('GUAZI_GONG', 'MAN_GONG', 'COUNTED_TRANSVERSE_SUPPORT'): continue
            d = dict(anchor, parent_jump_id=anchor['request_id'], request_id=anchor['request_id'] + '/' + role,
                     connector_in='', connector_out='', connector_status='UNRESOLVED')
            resolve(d, role, b, root, gen)
            if role in ('GUAZI_GONG', 'MAN_GONG', 'COUNTED_TRANSVERSE_SUPPORT'):
                d['support_layer'] = anchor['support_layer'] + '/' + role
            if role == 'COUNTED_TRANSVERSE_SUPPORT':
                d['allowed_roles_json'] = json.dumps([[x for x in combo if x not in excluded] for combo in allowed] if anchor['gong_stack'] == 'DOUBLE' else [])
            emit(g, d)

def cook_shared(node):
    g, owner = node.geometry(), node.parent()
    b, r, root = context(g, owner)
    clear_points(g)
    write_context(g, b, r, root)
    schema(g)
    seed = base_record(r)
    def add(role, layer, atom=False, generator='', **extra):
        d = dict(seed, role=role, support_layer=layer, request_id=r['recipe_id'] + '/SHARED/' + role)
        if atom or generator: resolve(d, role, b, root, generator)
        d.update(extra)
        return emit(g, d)
    if r['zone'] == 'PINGZUO' or r.get('status') == 'PARTIAL_RULE':
        add('PINGZUO_UNRESOLVED', 'PINGZUO_UNRESOLVED', status='PARTIAL_RULE', confidence='PARTIAL_RULE')
        return
    corner = r['position'] == 'CORNER'
    golden = r['recipe_id'] == GOLDEN
    role = 'LUDOU_CORNER' if corner else 'LUDOU_STANDARD'
    p = add(role, 'BASE', atom=True,
            mate_role='LANE_TOP_DATUM' if r['position'] == 'INTERCOLUMN' else 'COLUMN_TOP_DATUM')
    if golden:
        for k, v in dict(z_rule_status='RULE_DRIVEN', datum_known=1, datum_z_F=0., datum_z_m=0.,
                         connector_in='ASSEMBLY_BOTTOM_4P', connector_status='ASSEMBLY_DATUM_ONLY',
                         placement_status='EXPLICIT_BASE_DATUM').items(): p.setAttribValue(k, v)
    if corner:
        for role in ('PINGPAN_DOU', 'XIAOGONGTOU'):
            add(role, 'CORNER_CORE/' + role, atom=True)
        for role in ('CORNER_ANG', 'INNER_CORNER_ANG', 'YOU_ANG'):
            add(role, 'CORNER_' + role, generator='GEN_' + role,
                source_class='PROJECT_MVP', confidence='PLANNED_SEMANTIC')
        add('CORNER_BEAM_SUPPORT', 'CORNER_BEAM_SUPPORT', source_class='PROJECT_MVP', confidence='PROJECT_MVP')
    else:
        add('WALL_CORE_SYSTEM', 'WALL_CORE', source_class='PROJECT_MVP', confidence='SEMANTIC_INTERFACE')
    if golden:
        add('TOP_SUPPORT', 'TOP_SUPPORT', semantic_kind='DATUM', z_rule_status='RULE_DRIVEN',
            datum_known=1, datum_z_F=54., datum_z_m=54. * b['profile']['F_m'],
            connector_out='ASSEMBLY_UPPER_SUPPORT_4P', connector_status='ASSEMBLY_DATUM_ONLY',
            status='KNOWN_DATUM', P=(0., 0., 54. * b['profile']['F_m']),
            placement_status='EXPLICIT_SUPPORT_DATUM_METADATA')
    else:
        add('TOP_SUPPORT', 'TOP_SUPPORT')

def unresolved(p):
    return bool(p.attribValue('generator_id') or p.attribValue('missing_atom') or
                p.attribValue('z_rule_status') == 'UNRESOLVED' or p.attribValue('status') == 'PARTIAL_RULE')

def cook_filter(node, generators_only=False):
    g = node.geometry()
    g.deletePoints([p for p in g.points() if not (bool(p.attribValue('generator_id')) if generators_only else unresolved(p))])

def cook_debug(node):
    g = node.geometry()
    owner = node.parent()
    points = [record(p) for p in g.points() if p.attribValue('semantic_kind') == 'JUMP_ANCHOR']
    clear_points(g)
    origin = g.attribValue('branch_origin') if g.findGlobalAttrib('branch_origin') else (0., 0., 0.)
    previous = emit(g, dict(P=origin, semantic_kind='DEBUG_ROOT', production_source='SEMANTIC', enabled=1))
    if points:
        curve = g.createPolygon(is_closed=False)
        curve.addVertex(previous)
        for d in points:
            d['semantic_kind'] = 'DEBUG_ANCHOR'
            curve.addVertex(emit(g, d))

def cook_guides(node):
    g, owner = node.geometry(), node.parent()
    if not owner.evalParm('debug_branch'):
        clear_points(g)
    if owner.evalParm('show_unresolved'):
        u = owner.node('UNRESOLVED_FILTER').geometry()
        for p in u.points():
            emit(g, dict(record(p), semantic_kind='UNRESOLVED_GUIDE'))

def cook_preview(node):
    g, owner = node.geometry(), node.parent()
    requests = [record(p) for p in g.points() if p.attribValue('production_source') == 'ATOM' and
                not p.attribValue('missing_atom') and p.attribValue('enabled')]
    clear_points(g)
    if not owner.evalParm('preview_atoms'): return
    for d in requests:
        source = owner.node('ATOM_LIBRARY/' + d['asset_id'])
        if source is None: continue
        packed = g.createPackedGeometry(source.geometry())
        packed.setTransform(hou.Matrix4(hou.Quaternion(d['orient']).extractRotationMatrix3()))
        point = packed.points()[0]
        point.setPosition(d['P'])
        d.update(preview_only=1, placement_ready=0, placement_status='FIXED_ATOM_PLAN_PREVIEW_NOT_SOLVED')
        for k, v in d.items():
            if k != 'P' and g.findPointAttrib(k): point.setAttribValue(k, v)
    detail(g, 'preview_mode', 'PACKED_FIXED_ATOMS_AT_PLAN_DATUM; NOT VERTICAL ASSEMBLY')

def external_loader(node):
    g = node.geometry()
    owner = node.parent().node('YFS_DG_ASSEMBLY')
    b = load_bundle(owner)
    clear_points(g)
    detail(g, 'yfs_bundle_json', json.dumps(b))

def external_selector(node):
    g = node.geometry()
    owner = node.parent().node('YFS_DG_ASSEMBLY')
    b, r, root = context(g, owner)
    write_context(g, b, r, root)
