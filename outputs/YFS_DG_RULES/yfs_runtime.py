"""YFS v1 data/semantic runtime. No mesh loading, bbox inference or scaling."""
import json
import math
from pathlib import Path

FILES = {
    'profile': 'YFS_DG_PROFILE_v1.json',
    'atom_map': 'YFS_DG_ATOM_MAP_v1.json',
    'rules': 'YFS_DG_RULE_TABLE_v1.json',
    'recipes': 'YFS_DG_RECIPES_v1.json',
}


def scan_atoms(root):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('Atom root does not exist: ' + str(root))
    manifest_path = root / 'YFS_DG_ATOM_LIBRARY.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8-sig')) if manifest_path.exists() else {}
    metadata = {a['asset_id']: a for a in manifest.get('atoms', [])}
    found = {}
    for path in sorted((root / 'atoms').rglob('*')):
        if path.is_file() and path.suffix.lower() in ('.usd', '.usda', '.usdc', '.fbx', '.blend', '.obj', '.bgeo', '.glb') and path.stem.startswith('DG_'):
            asset_id = path.stem
            entry = found.setdefault(asset_id, {'asset_id': asset_id, 'files': {}, 'reuse_class': metadata.get(asset_id, {}).get('reuse_class', 'UNSPECIFIED')})
            entry['files'][path.suffix[1:]] = path.relative_to(root).as_posix()
    return found


def load_bundle(rules_dir, atom_root):
    bundle = {key: json.loads((Path(rules_dir) / name).read_text(encoding='utf-8-sig')) for key, name in FILES.items()}
    bundle['inventory'] = scan_atoms(atom_root)
    bundle['resolved_roles'] = {}
    for entry in bundle['atom_map']['roles']:
        asset_id = entry.get('asset_id')
        # Previously missing roles can resolve against a changed library, but only if present.
        if not asset_id:
            asset_id = next((a for a in entry['candidate_asset_ids'] if a in bundle['inventory']), '')
        present = bool(asset_id and asset_id in bundle['inventory'])
        bundle['resolved_roles'][entry['role']] = {'asset_id': asset_id if present else '', 'status': 'AVAILABLE' if present else 'MISSING'}
    return bundle


def validate(bundle, strict_assets=True):
    rules = bundle['rules']
    recipes = bundle['recipes']['recipes']
    ids = [r['recipe_id'] for r in recipes]
    assert len(ids) == len(set(ids)), 'Duplicate recipe_id'
    lookup = {r['puzuo']: r['jump_count'] for r in rules['standard_puzuo']}
    assert lookup == {p: p - 3 for p in range(4, 9)}, 'STANDARD_PUZUO lookup'
    generators = {g['generator_id']: g for g in rules['generator_registry']}
    for entry in bundle['atom_map']['roles']:
        if strict_assets and entry.get('asset_id'):
            assert entry['asset_id'] in bundle['inventory'], 'Fixed asset absent: ' + entry['asset_id']
    for gen in generators.values():
        assert gen['status'] == 'PLANNED' and not gen.get('asset_id'), 'Generator cannot bind mesh'
    scale = rules['validation_rules']['scale_policy']
    assert scale == {'allow_negative_scale': False, 'canonical_allow_non_uniform_scale': False, 'v1_scale': [1, 1, 1]}
    for r in recipes:
        assert r['zone'] in rules['enums']['zone']
        assert r['position'] in rules['enums']['position']
        assert r['system_type'] in rules['enums']['system_type']
        if r['status'] == 'PARTIAL_RULE':
            assert r['zone'] == 'PINGZUO' and not r['branches']
            continue
        assert r['puzuo'] in rules['zone_constraints'][r['zone']]['allowed_puzuo']
        assert r['system_type'] == 'STANDARD_PUZUO'
        if r['position'] == 'CORNER':
            assert r['base']['required_roles'] == ['LUDOU_CORNER']
            assert [(b['branch'], b['angle_deg']) for b in r['branches']] == [('FRONT', 0), ('RETURN', 90), ('CORNER', 45)]
        for branch in r['branches']:
            assert len(branch['jumps']) == lookup[branch['effective_puzuo']], 'Branch jump count'
            assert [j['jump_index'] for j in branch['jumps']] == list(range(1, len(branch['jumps']) + 1))
            for j in branch['jumps']:
                for name in ('jump_type', 'heart_mode', 'gong_stack'):
                    assert j[name] in rules['enums'][name]
                if r['zone'] == 'INTERIOR_SLOT' or branch['branch'] == 'IN':
                    assert j['jump_type'] == 'CHAO'
                if j['jump_type'] != 'CHAO':
                    assert not j['required_roles'] and j['required_generators'], 'Ang requires semantic generator'
                for role in j['required_roles']:
                    assert role in bundle['resolved_roles']
                for gen in j['required_generators']:
                    assert gen in generators
    return True


def select_recipe(bundle, recipe_id):
    matches = [r for r in bundle['recipes']['recipes'] if r['recipe_id'] == recipe_id]
    if len(matches) != 1:
        raise ValueError('Unknown or duplicate recipe_id: ' + recipe_id)
    return matches[0]


def semantic_points(bundle, recipe):
    """One BASE, one JUMP per branch/index, plus COUNTED support templates.

    P is a plan datum only; z=0 is unresolved, never a connector/mesh placement.
    Angles are clockwise from +Y toward +X; orient is quaternion xyzw.
    """
    if recipe['status'] == 'PARTIAL_RULE':
        return []
    result = []
    def add(kind, branch, index, jump_type, heart, stack, role, gen, angle, radius_F):
        radians = math.radians(angle)
        distance = radius_F * bundle['profile']['F_m']
        result.append({
            'recipe_id': recipe['recipe_id'], 'zone': recipe['zone'], 'position': recipe['position'],
            'branch': branch, 'jump_index': index, 'jump_type': jump_type,
            'heart_mode': heart, 'gong_stack': stack, 'role': role,
            'asset_id': '', 'generator_id': gen, 'semantic_kind': kind,
            'placement_status': 'PLAN_DATUM_ONLY_Z_UNRESOLVED', 'placement_ready': 0,
            'P': [distance * math.sin(radians), distance * math.cos(radians), 0.0],
            'orient': [0.0, 0.0, -math.sin(radians / 2), math.cos(radians / 2)],
            'radius_F': float(radius_F), 'confidence': recipe['confidence'], 'source_class': recipe['source_class'],
        })
    for role in recipe['base']['required_roles']:
        add('BASE', 'BASE', 0, '', '', '', role, '', 0, 0)
    for branch in recipe['branches']:
        for jump in branch['jumps']:
            radius = jump['jump_index'] * bundle['profile']['base_jump_F']
            if branch['branch'] == 'CORNER':
                radius *= math.sqrt(2)
            args = (branch['branch'], jump['jump_index'], jump['jump_type'], jump['heart_mode'], jump['gong_stack'])
            for role in jump['required_roles']:
                add('JUMP', *args, role, '', branch['angle_deg'], radius)
            for gen in jump['required_generators']:
                add('JUMP', *args, jump['jump_type'], gen, branch['angle_deg'], radius)
            if jump['heart_mode'] == 'COUNTED':
                add('TRANSVERSE_SUPPORT_TEMPLATE', *args, 'TRANSVERSE_SUPPORT_SYSTEM',
                    bundle['rules']['heart_rules']['COUNTED']['generator_id'], branch['angle_deg'], radius)
    return result


def resolve_points(bundle, points):
    registry = {g['generator_id']: g for g in bundle['rules']['generator_registry']}
    for p in points:
        if p['generator_id']:
            p['asset_id'] = ''
            p['resolution_status'] = registry[p['generator_id']]['status']
        else:
            mapping = bundle['resolved_roles'][p['role']]
            p['asset_id'] = mapping['asset_id']
            p['resolution_status'] = mapping['status']
    return points


def cook(stage, hou):
    node = hou.pwd()
    geo = node.geometry()
    parent = node.parent()
    def detail(name, value):
        if not geo.findGlobalAttrib(name):
            geo.addAttrib(hou.attribType.Global, name, value)
        geo.setGlobalAttribValue(name, value)
    if stage == 'loader':
        bundle = load_bundle(parent.evalParm('rules_dir'), parent.evalParm('atom_root'))
        validate(bundle, strict_assets=False)
        detail('yfs_bundle_json', json.dumps(bundle))
        detail('profile_id', bundle['profile']['profile_id'])
        detail('F_m', bundle['profile']['F_m'])
        detail('M_m', bundle['profile']['M_m'])
        detail('asset_root', parent.evalParm('atom_root'))
        detail('missing_roles_json', json.dumps([k for k, v in bundle['resolved_roles'].items() if v['status'] == 'MISSING']))
        detail('mesh_instancing_ready', 0)
        return
    bundle = json.loads(geo.attribValue('yfs_bundle_json'))
    if stage == 'selector':
        recipe = select_recipe(bundle, parent.evalParm('recipe_id'))
        detail('selected_recipe_json', json.dumps(recipe))
        detail('recipe_status', recipe['status'])
        detail('puzuo', recipe['puzuo'] or 0)
        is_golden = recipe['recipe_id'] == 'YFS_4P_EXT_COLUMNHEAD_STANDARD'
        detail('golden_metadata_applicable', int(is_golden))
        detail('golden_reference_json', json.dumps(bundle['profile']['golden_4p'] if is_golden else {}))
        if is_golden:
            detail('golden_support_local_z_F', 54.0)
            detail('golden_bbox_top_F', 58.0)
        return
    recipe = json.loads(geo.attribValue('selected_recipe_json'))
    if stage == 'branches':
        points = semantic_points(bundle, recipe)
        string_attrs = ('recipe_id zone position branch jump_type heart_mode gong_stack role asset_id generator_id semantic_kind placement_status confidence source_class resolution_status').split()
        for name in string_attrs:
            geo.addAttrib(hou.attribType.Point, name, '')
        for name in ('jump_index', 'placement_ready'):
            geo.addAttrib(hou.attribType.Point, name, 0)
        geo.addAttrib(hou.attribType.Point, 'radius_F', 0.0)
        verb = hou.sopNodeTypeCategory().nodeVerb('attribcreate::2.0')
        verb.setParms({'numattr': ({'name#': 'orient', 'enable#': 1, 'class#': 2, 'type#': 0,
                                   'typeinfo#': 6, 'size#': 4,
                                   'default#v': (0.0, 0.0, 0.0, 1.0), 'writevalues#': 0},)})
        orient_schema = hou.Geometry()
        verb.execute(orient_schema, [])
        geo.merge(orient_schema)
        for item in points:
            point = geo.createPoint()
            point.setPosition(item['P'])
            for key, value in item.items():
                if key != 'P':
                    point.setAttribValue(key, tuple(value) if isinstance(value, list) else value)
        detail('point_layout_contract', 'BASE + JUMP + COUNTED TRANSVERSE_SUPPORT_TEMPLATE; filter semantic_kind=JUMP to count jumps. P is plan datum, z unresolved.')
        detail('gong_stack_semantic_json', json.dumps(bundle['rules']['gong_stack_semantic']))
        detail('excluded_roles_json', json.dumps(recipe.get('excluded_roles', [])))
    elif stage == 'resolver':
        registry = {g['generator_id']: g for g in bundle['rules']['generator_registry']}
        for point in geo.points():
            gen = point.attribValue('generator_id')
            if gen:
                point.setAttribValue('asset_id', '')
                point.setAttribValue('resolution_status', registry[gen]['status'])
            else:
                mapping = bundle['resolved_roles'][point.attribValue('role')]
                point.setAttribValue('asset_id', mapping['asset_id'])
                point.setAttribValue('resolution_status', mapping['status'])
