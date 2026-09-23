import hou, json, shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
OLD=ROOT/'baseline'
OUT=ROOT/'outputs'; RULES=OUT/'YFS_DG_RULES'; HDA=OUT/'hda/YFS_DG_GOLDEN_4P_v1.hda'; HIP=OUT/'YFS_DG_GOLDEN_4P_v1.hip'
RULES.mkdir(parents=True,exist_ok=True); HDA.parent.mkdir(parents=True,exist_ok=True)
for f in (OLD/'YFS_DG_RULES').iterdir():
    if f.suffix in ('.json','.py') and not f.name.endswith('_QA.json'): shutil.copy2(f,RULES/f.name)
exec(compile((ROOT/'tools/make_golden_template.py').read_text(encoding='utf-8'),'make_golden_template.py','exec'))
for lib in (OLD/'hda').glob('*.hda'): hou.hda.installFile(str(lib))
hou.hipFile.load(str(OLD/'YFS_DG_VERTICAL_ANG_v1.hip'),suppress_save_prompt=True,ignore_load_warnings=True)
hou.hipFile.setName(str(HIP)); hou.putenv('HIP',OUT.as_posix())
hou.putenv('YFS_DG_ATOM_ROOT',(ROOT/'assets/atom_library').as_posix())
hou.hscript('upaxis z')
obj=hou.node('/obj/YFS_DG_RULE_SYSTEM'); assembly=obj.node('YFS_DG_ASSEMBLY'); vertical=obj.node('YFS_DG_VERTICAL_SOLVER')
runtime=(ROOT/'tools/golden_runtime.py').read_text(encoding='utf-8')
template=(RULES/'YFS_DG_GOLDEN_4P_ASSEMBLY_v1.json').read_text(encoding='utf-8'); data=json.loads(template)

def templateparm():
    p=hou.StringParmTemplate('golden_template_file','Golden 4P Template',1,default_value=('$HIP/YFS_DG_RULES/YFS_DG_GOLDEN_4P_ASSEMBLY_v1.json',))
    p.setStringType(hou.stringParmType.FileReference); return p

# New solver version leaves the previous deliverable's definition untouched.
vertical.type().definition().copyToHDAFile(str(HDA),new_name='yfs::dg_vertical_solver::1.1',new_menu_name='YFS DG Vertical Solver + Golden 4P')
hou.hda.installFile(str(HDA))
d=next(d for d in hou.hda.definitionsInFile(str(HDA)) if d.nodeTypeName()=='yfs::dg_vertical_solver::1.1')
src=d.sections()['PythonModule'].contents()
src=src.replace('unresolved=sum(not d[\'z_resolved\'] for d in data)',"golden_solve(node)\n unresolved=sum(not p.attribValue('z_resolved') for p in g.points())")
d.addSection('PythonModule',src+'\n'+runtime)
pg=d.parmTemplateGroup(); pg.append(templateparm()); d.setParmTemplateGroup(pg)
d.addSection('YFS_DG_GOLDEN_4P_ASSEMBLY_v1.json',template); d.save(str(HDA),create_backup=False)
vertical=vertical.changeNodeType('yfs::dg_vertical_solver::1.1',keep_name=True,keep_parms=True)

gold=obj.createNode('subnet','YFS_DG_GOLDEN_4P_ASSEMBLER')
pg=hou.ParmTemplateGroup()
for p in [hou.ToggleParmTemplate('enabled','Generate Full Golden 4P',default_value=True),templateparm(),hou.StringParmTemplate('atom_root','Atom Root',1,default_value=('$YFS_DG_ATOM_ROOT',))]: pg.append(p)
gold.setParmTemplateGroup(pg)
library=gold.createNode('subnet','ATOM_LIBRARY')
for aid in sorted(set(i['asset_id'] for i in data['instances'])):
    n=library.createNode('usdimport',aid)
    n.parm('filepath1').set('`chs("../../atom_root")`/atoms/'+aid+'.usd')
    n.parm('primpattern').set('/*'); n.parm('input_unpack').set(1)
    n.parm('unpack_geomtype').set(1)
library.layoutChildren()
for idx,name,fn in [(0,'OUT_PACKED','golden_pack'),(1,'OUT_CONNECTORS','golden_connectors')]:
    n=gold.createNode('python',name); n.setInput(0,gold.indirectInputs()[0])
    n.parm('python').set('hou.pwd().parent().hdaModule().'+fn+'(hou.pwd())')
    o=gold.createNode('output','OUTPUT_'+str(idx));o.parm('outputidx').set(idx);o.setInput(0,n)
    if idx==0: n.setDisplayFlag(True);n.setRenderFlag(True)
gold.layoutChildren()
gold=gold.createDigitalAsset(name='yfs::dg_golden_4p_assembler::1.0',hda_file_name=str(HDA),description='YFS Golden 4P Assembler',min_num_inputs=1,max_num_inputs=1,create_backup=False)
d=gold.type().definition();d.setParmTemplateGroup(pg);d.addSection('PythonModule',runtime);d.addSection('YFS_DG_GOLDEN_4P_ASSEMBLY_v1.json',template)
d.setComment('21 source instances, 12 shared canonical USD atoms. Golden 4P only.');d.save(str(HDA),create_backup=False);gold.matchCurrentDefinition()
gold.setInput(0,vertical)

pg=obj.parmTemplateGroup()
for p in [hou.ToggleParmTemplate('generate_full_golden_4p','Generate Full Golden 4P',default_value=True),hou.ToggleParmTemplate('preview_fixed_atoms','Preview Fixed Atoms (Other Recipes)',default_value=False),hou.ToggleParmTemplate('show_debug_guides','Show Debug Guides',default_value=False)]:
    if not pg.find(p.name()): pg.append(p)
obj.setParmTemplateGroup(pg)
obj.parm('generate_full_golden_4p').set(1);obj.parm('preview_fixed_atoms').set(0);obj.parm('show_debug_guides').set(0)
obj.parm('rules_dir').set('$HIP/YFS_DG_RULES');obj.parm('atom_root').set('$YFS_DG_ATOM_ROOT')
# Assembly is the recipe authority; both its menu and the object-level proxy remain usable.
assembly.parm('recipe_id').set(data['recipe_id'])
assembly.parm('atom_root').setExpression('chs("../atom_root")')
obj.parm('recipe_id').setExpression('chs("YFS_DG_ASSEMBLY/recipe_id")')
assembly.parm('preview_atoms').setExpression('int(hou.pwd().parent().evalParm("preview_fixed_atoms") and hou.pwd().evalParm("recipe_id") != "YFS_4P_EXT_COLUMNHEAD_STANDARD")',hou.exprLanguage.Python)
gold.parm('enabled').setExpression('ch("../generate_full_golden_4p")')
gold.parm('atom_root').setExpression('chs("../atom_root")')
gold.parm('golden_template_file').setExpression('chs("../YFS_DG_VERTICAL_SOLVER/golden_template_file")')

def null(name,up,index=0):
    n=obj.node(name) or obj.createNode('null',name);n.setInput(0,up,index);return n
full=null('OUT_GOLDEN_4P_FULL',gold)
null('OUT_GOLDEN_4P_CONNECTORS',gold,1)
null('OUT_SEMANTIC_REQUESTS',assembly)
null('OUT_UNRESOLVED',vertical,1)
debug=obj.createNode('merge','MERGE_GOLDEN_AND_EXISTING_DEBUG');debug.setInput(0,vertical,2);debug.setInput(1,obj.node('YFS_DG_ANG_GENERATOR'),2);debug.setInput(2,gold,1)
null('OUT_DEBUG',debug)
select=obj.createNode('switch','SELECT_RECIPE_GEOMETRY');select.setInput(0,obj.node('MERGE_FIXED_AND_ANG_PREVIEW'));select.setInput(1,full)
select.parm('input').setExpression('int(hou.pwd().parent().node("YFS_DG_ASSEMBLY").evalParm("recipe_id") == "YFS_4P_EXT_COLUMNHEAD_STANDARD")',hou.exprLanguage.Python)
null('OUTPUT',select)
debug_view=obj.node('DISPLAY_PREVIEW_AND_GUIDES')
for idx in range(len(debug_view.inputs())): debug_view.setInput(idx,None)
debug_view.setInput(0,select);debug_view.setInput(1,debug)
view=obj.createNode('switch','VIEWPORT_OUTPUT');view.setInput(0,select);view.setInput(1,debug_view)
view.parm('input').setExpression('ch("../show_debug_guides")')
view.setDisplayFlag(True);obj.node('OUTPUT').setRenderFlag(True)
full.setComment('Full Golden 4P only. 21 packed instances / 12 canonical atoms. Support 54F; bbox reference 58F.')
vertical.setComment('Golden fixed parts EXACT_GOLDEN. Other recipes retain original unresolved policy.')
obj.layoutChildren();obj.setSelected(True,clear_all_selected=True)
for n in [vertical,gold,full,view]:
    try: n.cook(force=True)
    except hou.OperationFailed:
        print('ERRORS',[(x.path(),x.errors()) for x in [n]+list(n.allSubChildren()) if x.errors()],flush=True)
        raise
    print('COOK',n.name(),n.errors(),len(n.geometry().prims()),len(n.geometry().points()),flush=True)
    if n.errors(): raise RuntimeError(n.errors())
print('BBOX',full.geometry().boundingBox(),flush=True)
# Make the HIP self-contained for HDA definitions; Atom USD files stay in the existing library.
for name in ['yfs::dg_assembly::1.0','yfs::dg_branch::1.0','yfs::dg_jump::1.0','yfs::dg_vertical_solver::1.1','yfs::dg_ang_generator::1.0','yfs::dg_golden_4p_assembler::1.0']:
    typ=hou.nodeType(hou.sopNodeTypeCategory(),name)
    typ.definition().copyToHDAFile('Embedded')
    next(d for d in typ.allInstalledDefinitions() if d.libraryFilePath()=='Embedded').setIsPreferred(True)
shutil.copy2(ROOT/'tools/golden_runtime.py',RULES/'yfs_golden_4p_runtime.py')
hou.hipFile.save(str(HIP))
print('SAVED',HIP,flush=True)
