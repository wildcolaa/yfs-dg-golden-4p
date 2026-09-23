# Golden 4P 实施报告

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
