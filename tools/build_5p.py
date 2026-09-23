import hou,json,runpy,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'outputs';RULES=OUT/'YFS_DG_RULES'
HDA=OUT/'hda/YFS_DG_5P_ATOM_COMPAT_v1.hda';HIP=OUT/'YFS_DG_5P_ATOM_COMPAT_v1.hip'
runpy.run_path(str(ROOT/'tools/make_5p_template.py'))
RID='YFS_5P_EXT_COLUMNHEAD_GENERIC_ATOM_COMPAT'
hou.hipFile.load(str(OUT/'YFS_DG_GOLDEN_4P_v1.hip'),suppress_save_prompt=True,ignore_load_warnings=False)
hou.hipFile.setName(str(HIP));hou.putenv('HIP',OUT.as_posix());hou.putenv('YFS_DG_ATOM_ROOT',(ROOT/'assets/atom_library').as_posix());hou.hscript('upaxis z')
obj=hou.node('/obj/YFS_DG_RULE_SYSTEM')
runtime=(ROOT/'tools/assembly_5p_runtime.py').read_text(encoding='utf-8')
template=(RULES/'YFS_DG_5P_ASSEMBLY_v1.json').read_text(encoding='utf-8');data=json.loads(template)

def clone(node,typename,label):
    node.type().definition().copyToHDAFile(str(HDA),new_name=typename,new_menu_name=label)
    hou.hda.installFile(str(HDA))
    return next(d for d in hou.hda.definitionsInFile(str(HDA)) if d.nodeTypeName()==typename)
def fileparm():
    p=hou.StringParmTemplate('assembly_template_file','5P Assembly Template',1,default_value=('$HIP/YFS_DG_RULES/YFS_DG_5P_ASSEMBLY_v1.json',))
    p.setStringType(hou.stringParmType.FileReference);return p

a=obj.node('YFS_DG_ASSEMBLY');d=clone(a,'yfs::dg_assembly::1.1','YFS Assembly + 5P Project Recipe')
src=d.sections()['PythonModule'].contents().replace('YFS_DG_RECIPES_v1.json','YFS_DG_RECIPES_v2.json')
d.addSection('PythonModule',src)
b=json.loads(d.sections()['YFSBundle.json'].contents());b['recipes']=json.loads((RULES/'YFS_DG_RECIPES_v2.json').read_text(encoding='utf-8'))
d.addSection('YFSBundle.json',json.dumps(b,ensure_ascii=False));d.save(str(HDA),create_backup=False)
a=a.changeNodeType('yfs::dg_assembly::1.1',keep_name=True,keep_parms=True)
obj.node('YFS_DG_RULE_LOADER').parm('python').set('hou.pwd().parent().node("YFS_DG_ASSEMBLY").hdaModule().external_loader(hou.pwd())')
obj.node('YFS_DG_RECIPE_SELECTOR').parm('python').set('hou.pwd().parent().node("YFS_DG_ASSEMBLY").hdaModule().external_selector(hou.pwd())')

v=obj.node('YFS_DG_VERTICAL_SOLVER');d=clone(v,'yfs::dg_vertical_solver::1.2','YFS Vertical Solver 4P + 5P Project')
src=d.sections()['PythonModule'].contents().replace('YFS_DG_VERTICAL_RULES_v1.json','YFS_DG_VERTICAL_RULES_v2.json')
assert 'golden_solve(node)\n unresolved=' in src
src=src.replace('golden_solve(node)\n unresolved=','golden_solve(node)\n p5_solve(node)\n unresolved=')
src+='\n'+runtime+'''
_original_anchor_debug=cook_anchor_debug
def cook_anchor_debug(node):
    _original_anchor_debug(node)
    if node.parent().evalParm('show_anchor_debug'):p5_debug(node)
'''
d.addSection('PythonModule',src);pg=d.parmTemplateGroup();pg.append(fileparm());d.setParmTemplateGroup(pg)
d.addSection('YFS_DG_5P_ASSEMBLY_v1.json',template);d.addSection('YFS_DG_VERTICAL_RULES_v2.json',(RULES/'YFS_DG_VERTICAL_RULES_v2.json').read_text(encoding='utf-8'))
d.save(str(HDA),create_backup=False);v=v.changeNodeType('yfs::dg_vertical_solver::1.2',keep_name=True,keep_parms=True)
v.parm('vertical_rule_file').set('$HIP/YFS_DG_RULES/YFS_DG_VERTICAL_RULES_v2.json')

ang=obj.node('YFS_DG_ANG_GENERATOR');d=clone(ang,'yfs::dg_ang_generator::1.1','YFS ANG Generator + 5P Body Preview')
src=d.sections()['PythonModule'].contents().replace('YFS_DG_ANG_PRESETS_v1.json','YFS_DG_ANG_PRESETS_v2.json')
src+='\n'+runtime+'''
_original_evaluate=evaluate
def evaluate(d,b,r):
    out=_original_evaluate(d,b,r)
    if d.get('recipe_id')==P5_RECIPE:
        out['nominal_length_status']='USER_SPECIFIED_PROJECT_CONSTRAINT'
        out['length_relation']='PROJECT_NOMINAL_PREVIEW_NOT_BEAM_ENDPOINTS'
    return out
_original_cook_mesh=cook_mesh
def cook_mesh(node):
    _original_cook_mesh(node)
    p5_tag_generated(node)
'''
d.addSection('PythonModule',src);d.addSection('YFS_DG_ANG_PRESETS_v2.json',(RULES/'YFS_DG_ANG_PRESETS_v2.json').read_text(encoding='utf-8'))
d.save(str(HDA),create_backup=False);ang=ang.changeNodeType('yfs::dg_ang_generator::1.1',keep_name=True,keep_parms=True)
ang.parm('preset_file').set('$HIP/YFS_DG_RULES/YFS_DG_ANG_PRESETS_v2.json')

pack=obj.createNode('subnet','YFS_DG_5P_TEMPLATE_ASSEMBLER');pg=hou.ParmTemplateGroup()
for p in [hou.ToggleParmTemplate('enabled','Generate 5P Project Assembly',default_value=True),fileparm(),hou.StringParmTemplate('atom_root','Atom Root',1,default_value=('$YFS_DG_ATOM_ROOT',))]:pg.append(p)
pack.setParmTemplateGroup(pg);lib=pack.createNode('subnet','ATOM_LIBRARY')
for aid in sorted(set(i['asset_id'] for i in data['instances'])):
    n=lib.createNode('usdimport',aid);n.parm('filepath1').set('`chs("../../atom_root")`/atoms/'+aid+'.usd')
    n.parm('primpattern').set('/*');n.parm('input_unpack').set(1);n.parm('unpack_geomtype').set(1)
lib.layoutChildren()
for idx,fn,name in [(0,'p5_pack','OUT_FIXED_ATOMS'),(1,'p5_connectors','OUT_CONNECTORS')]:
    n=pack.createNode('python',name);n.setInput(0,pack.indirectInputs()[0]);n.parm('python').set('hou.pwd().parent().hdaModule().'+fn+'(hou.pwd())')
    out=pack.createNode('output','OUTPUT_'+str(idx));out.parm('outputidx').set(idx);out.setInput(0,n)
    if idx==0:n.setDisplayFlag(True);n.setRenderFlag(True)
pack.layoutChildren();pack=pack.createDigitalAsset(name='yfs::dg_template_atom_assembler::1.0',hda_file_name=str(HDA),description='YFS Template Atom Assembler (5P Project)',min_num_inputs=1,max_num_inputs=1,create_backup=False)
d=pack.type().definition();d.setParmTemplateGroup(pg);d.addSection('PythonModule',runtime);d.addSection('YFS_DG_5P_ASSEMBLY_v1.json',template)
onload='''import hou
from pathlib import Path
def open_5p():
    root=Path(hou.expandString('$HIP/../assets/atom_library'))
    current=Path(hou.getenv('YFS_DG_ATOM_ROOT') or '')
    if not (current/'YFS_DG_ATOM_LIBRARY.json').is_file() and (root/'YFS_DG_ATOM_LIBRARY.json').is_file():hou.putenv('YFS_DG_ATOM_ROOT',root.as_posix())
    if hou.isUIAvailable():
        rig=hou.node('/obj/YFS_DG_RULE_SYSTEM')
        if rig and rig.node('YFS_DG_ASSEMBLY').evalParm('recipe_id')=='YFS_5P_EXT_COLUMNHEAD_GENERIC_ATOM_COMPAT':
            sv=hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
            if sv:
                sv.setPwd(hou.node('/obj'));sv.curViewport().homeBoundingBox(hou.BoundingBox(-.85,-1.15,-.05,.85,1.6,1.25))
if hou.isUIAvailable():
    import hdefereval
    hdefereval.executeDeferred(open_5p)
else:open_5p()
'''
d.addSection('OnLoaded',onload);d.setExtraFileOption('OnLoaded/IsPython',True);d.save(str(HDA),create_backup=False);pack.matchCurrentDefinition();pack.setInput(0,v)

pg=obj.parmTemplateGroup();pg.append(hou.ToggleParmTemplate('generate_5p_project','Generate 5P Project Assembly',default_value=True))
recipeparm=pg.find('recipe_id');recipeparm.setItemGeneratorScript('(lambda n: n.hdaModule().menu({"node":n}))(kwargs["node"].node("YFS_DG_ASSEMBLY"))');recipeparm.setItemGeneratorScriptLanguage(hou.scriptLanguage.Python);pg.replace('recipe_id',recipeparm)
pg.append(hou.LabelParmTemplate('p5_scope','5P Scope',column_labels=('Project Atom-compatible; ANG tail / riding-beam interface unresolved.',)))
obj.setParmTemplateGroup(pg);obj.parm('generate_5p_project').set(1)
pack.parm('enabled').setExpression('ch("../generate_5p_project")');pack.parm('atom_root').setExpression('chs("../atom_root")')
pack.parm('assembly_template_file').setExpression('chs("../YFS_DG_VERTICAL_SOLVER/assembly_template_file")')
a.parm('preview_atoms').setExpression('int(hou.pwd().parent().evalParm("preview_fixed_atoms") and hou.pwd().evalParm("recipe_id") not in ("YFS_4P_EXT_COLUMNHEAD_STANDARD","'+RID+'"))',hou.exprLanguage.Python)
def null(name,up,idx=0):
    n=obj.createNode('null',name);n.setInput(0,up,idx);return n
fixed=null('OUT_5P_FIXED_ATOMS',pack);conns=null('OUT_5P_CONNECTORS',pack,1)
combined=obj.createNode('merge','MERGE_5P_FIXED_AND_ANG');combined.setInput(0,fixed);combined.setInput(1,obj.node('ANG_PREVIEW_ENABLE'))
enable=obj.createNode('switch','ENABLE_5P_FULL');enable.setInput(0,obj.node('EMPTY_PREVIEW'));enable.setInput(1,combined);enable.parm('input').setExpression('ch("../generate_5p_project")')
full=null('OUT_5P_FULL_PROJECT',enable)
gate=obj.createNode('switch','ISOLATE_5P_OUTPUT');gate.setInput(0,obj.node('EMPTY_PREVIEW'));gate.setInput(1,enable)
gate.parm('input').setExpression('int(hou.pwd().parent().node("YFS_DG_ASSEMBLY").evalParm("recipe_id")=="'+RID+'")',hou.exprLanguage.Python);full.setInput(0,gate)
select=obj.node('SELECT_RECIPE_GEOMETRY');select.setInput(2,full)
select.parm('input').setExpression('{"YFS_4P_EXT_COLUMNHEAD_STANDARD":1,"'+RID+'":2}.get(hou.pwd().parent().node("YFS_DG_ASSEMBLY").evalParm("recipe_id"),0)',hou.exprLanguage.Python)
obj.node('MERGE_GOLDEN_AND_EXISTING_DEBUG').setInput(3,conns)
a.parm('recipe_id').set(RID);obj.parm('show_debug_guides').set(0)
full.setComment('41 existing Atom instances + one PROJECT_PREVIEW down-ang. Beam/tail endpoints remain unresolved.')
obj.layoutChildren();obj.setSelected(True,clear_all_selected=True)
for n in [a,v,pack,ang,full,obj.node('VIEWPORT_OUTPUT')]:
    try:n.cook(force=True)
    except hou.OperationFailed:
        print('ERRORS',[(x.path(),x.errors()) for x in [n]+list(n.allSubChildren()) if x.errors()],flush=True);raise
    print('COOK',n.name(),len(n.geometry().prims()),len(n.geometry().points()),n.errors(),flush=True)
types=['yfs::dg_assembly::1.1','yfs::dg_branch::1.0','yfs::dg_jump::1.0','yfs::dg_vertical_solver::1.2','yfs::dg_ang_generator::1.1','yfs::dg_golden_4p_assembler::1.0','yfs::dg_template_atom_assembler::1.0']
for name in types:
    typ=hou.nodeType(hou.sopNodeTypeCategory(),name);typ.definition().copyToHDAFile('Embedded');next(d for d in typ.allInstalledDefinitions() if d.libraryFilePath()=='Embedded').setIsPreferred(True)
shutil.copy2(ROOT/'tools/assembly_5p_runtime.py',RULES/'yfs_assembly_5p_runtime.py')
hou.hipFile.save(str(HIP));print('SAVED',HIP,'BBOX',full.geometry().boundingBox(),flush=True)
