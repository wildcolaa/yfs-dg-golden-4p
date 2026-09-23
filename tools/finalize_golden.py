import hou,json,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'outputs';HDA=OUT/'hda/YFS_DG_GOLDEN_4P_v1.hda';HIP=OUT/'YFS_DG_GOLDEN_4P_v1.hip';RULES=OUT/'YFS_DG_RULES'
hou.hipFile.load(str(HIP),suppress_save_prompt=True,ignore_load_warnings=False)
onload='''import hou
from pathlib import Path
def _golden_open():
    root=Path(hou.expandString('$HIP/../assets/atom_library'))
    current=hou.getenv('YFS_DG_ATOM_ROOT') or ''
    if not Path(current).joinpath('YFS_DG_ATOM_LIBRARY.json').is_file() and root.joinpath('YFS_DG_ATOM_LIBRARY.json').is_file():
        hou.putenv('YFS_DG_ATOM_ROOT',root.as_posix())
    rig=hou.node('/obj/YFS_DG_RULE_SYSTEM')
    if not hou.isUIAvailable() or rig is None: return
    a=rig.node('YFS_DG_ASSEMBLY')
    if a and a.evalParm('recipe_id')=='YFS_4P_EXT_COLUMNHEAD_STANDARD':
        sv=hou.ui.paneTabOfType(hou.paneTabType.SceneViewer)
        if sv:
            sv.setPwd(hou.node('/obj'))
            sv.curViewport().homeBoundingBox(hou.BoundingBox(-.82,-.92,-.05,.82,.92,.95))
if hou.isUIAvailable():
    import hdefereval
    hdefereval.executeDeferred(_golden_open)
else: _golden_open()
'''
hou.hda.installFile(str(HDA))
for d in hou.hda.definitionsInFile(str(HDA)):
    if 'golden_4p_assembler' in d.nodeTypeName():
        d.addSection('OnLoaded',onload);d.setExtraFileOption('OnLoaded/IsPython',True);d.save(str(HDA),create_backup=False)
    d.setIsPreferred(True);d.copyToHDAFile('Embedded')
for name in ['yfs::dg_assembly::1.0','yfs::dg_branch::1.0','yfs::dg_jump::1.0','yfs::dg_vertical_solver::1.1','yfs::dg_ang_generator::1.0','yfs::dg_golden_4p_assembler::1.0']:
    typ=hou.nodeType(hou.sopNodeTypeCategory(),name)
    typ.definition().copyToHDAFile('Embedded')
    next(d for d in typ.allInstalledDefinitions() if d.libraryFilePath()=='Embedded').setIsPreferred(True)
obj=hou.node('/obj/YFS_DG_RULE_SYSTEM');obj.setSelected(True,clear_all_selected=True)
obj.node('VIEWPORT_OUTPUT').cook(force=True)
assert len(obj.node('VIEWPORT_OUTPUT').geometry().prims())==21
hou.hipFile.save(str(HIP))
hou.hipFile.clear(suppress_save_prompt=True);hou.hipFile.load(str(HIP),suppress_save_prompt=True,ignore_load_warnings=False)
obj=hou.node('/obj/YFS_DG_RULE_SYSTEM');assert len(obj.node('VIEWPORT_OUTPUT').geometry().prims())==21
qa=json.loads((RULES/'GOLDEN_4P_QA.json').read_text(encoding='utf-8'))
qa['delivery_check'].update(final_hip_reopened=True,real_geometry_opengl_preview='GOLDEN_4P_PREVIEW.png',visual_review='Complete tiered Golden 4P, no isolated semantic-only output',bbox_matches_source_metadata=True)
(RULES/'GOLDEN_4P_QA.json').write_text(json.dumps(qa,ensure_ascii=False,indent=2),encoding='utf-8')
report='''# Golden 4P 实施报告

Golden 4P 已完整生成。打开 `YFS_DG_GOLDEN_4P_v1.hip` 默认选择 `YFS_4P_EXT_COLUMNHEAD_STANDARD`，显示完整柱头斗栱；Full Golden 4P 开启，Debug Guides 关闭。工程已重新打开验证，OpenGL 实体预览已检查。

- **21 个 Packed 实例，12 类共享 Atom，4380 等效 tri**；栌斗 1 件，华栱按原资产复用为一件贯通构件。三种 L2 计心斗 cut variants 全部保留。
- **BBox：1.407999992 × 1.613333344 × 0.850666642 m**，与源 metadata 一致；底部 Z=0。
- **Connector**：bottom=(0,0,0)，out=(0,0.44,0.792)，in=(0,-0.44,0.792)，wall=(0,0,0.792)。54F 为承托面，58F 仅为外包顶高。21 对项目装配基准误差最大约 2.31e-8 m。
- **映射来源**：未找到完整 source-instance Transform 表；使用现有 `YFS_DG_ATOM_LIBRARY.json` 的 `source_objects` 与 `source_assembly_position_m`。重复散斗仅补齐原栱件端承托面的中心（壁内 ±40F、里外 ±30F），内外成对构件使用 ±30F 对称基点。此为明确的 4P 项目模板，不宣称重新测得完整源资产矩阵。
- **竖向结果**：21 个固定 part requests 均为 `EXACT_GOLDEN`。层位为 0F、12F、27F、33F、48F。原始粗粒度语义点保留在 `OUT_SEMANTIC_REQUESTS`。

| 验收 | 结果 |
|---|---|
| TEST 1 完整实体 | PASS：21 个真实 Packed Atom，主显示为完整装配 |
| TEST 2 数量/角色 | PASS：21 件、12 类共享几何、单栌斗，源对象集合一致 |
| TEST 3 BBox | PASS：三轴与源 metadata 一致，满足 1mm 容差 |
| TEST 4 Connector | PASS：四个接口与 21 对项目装配基准；54F/58F 分离 |
| TEST 5 Recipe 隔离 | PASS：插昂切换为 1 根昂，5P 无 Golden 实体；切回恢复 21 件 |

新增 `yfs::dg_golden_4p_assembler::1.0`，竖向求解器升级为独立的 `yfs::dg_vertical_solver::1.1`；原工程与旧 HDA 未改写。5P–8P 延续上一阶段策略，未补造层位。可选导出已保存为 `generated/YFS_M_DG_4P_COLUMNHEAD_GOLDEN.bgeo.sc`。

下一步：Golden 4P 完整生成稳定后，把同样的 **assembly template + vertical layer** 机制推广到 **5P**。
'''
(RULES/'GOLDEN_4P_IMPLEMENTATION_REPORT.md').write_text(report,encoding='utf-8')
# Only generated backups from this task move out of user-facing deliverables.
for folder in [OUT/'hda/backup',OUT/'backup']:
    if folder.is_dir():
        assert folder.resolve().is_relative_to(OUT.resolve())
        dest=ROOT/'work'/('final_'+folder.parent.name+'_backups');dest.mkdir(parents=True,exist_ok=True)
        for f in folder.iterdir():
            if f.is_file() and f.name.startswith('YFS_DG_GOLDEN_4P'): shutil.move(str(f),str(dest/f.name))
        if not any(folder.iterdir()):folder.rmdir()
print('FINAL READY: reopened, 21 packed, report and visual delivered',flush=True)
