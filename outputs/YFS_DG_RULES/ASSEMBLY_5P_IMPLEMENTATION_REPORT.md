# 5P Atom-compatible 项目柱头装配

已新增独立 Recipe：`YFS_5P_EXT_COLUMNHEAD_GENERIC_ATOM_COMPAT`。打开 `YFS_DG_5P_ATOM_COMPAT_v1.hip` 默认显示完整项目装配：**41 个固定 Packed Atom + 1 根程序下昂，共 42 件**。固定件共享 **13 类现有 Atom**，包括两件瓜子栱，未新增或修改 Atom Mesh。

这是一版用户指定的 **PROJECT_5P_GENERIC**，不是梁栿／骑栿关系完全复原版。数值来自本次用户提供的项目规范；引用占位符未被视为已核验的历史来源。

| 项目 | 实测／实现 |
|---|---|
| 固定件层位 | 0、12、27、33、48、54、69F |
| 真实承托 Datum | 75F = 1.100m，`PROJECT_DERIVED / HIGH` |
| 顶部斗耳 BBox 参考 | 79F ≈ 1.158667m，不作为 Connector |
| 外／里第二跳 | ±60F = ±0.880m |
| 固定 Atom BBox | 1.408 × 1.994667 × 1.158667m |
| 含下昂项目预览的完整 BBox | 1.408 × 2.481303 × 1.158667m |
| 固定件位置最大误差 | 约 4.23e-8m，相对用户给定 P/F |

Connector：bottom=(0,0,0)，outboard=(0,0.880,1.100)，inboard=(0,-0.880,1.100)，wall=(0,0,1.100)。模板记录 41 对项目装配基准；它们用于验证位置配对，不代表已验证榫口穿插、接触面或结构承载。

## 下昂：承托控制段与整根预览分离

保留四个明确的承托控制点：上皮 `(0,30,59.25) → (0,60,48)F`，下皮 `(0,30,44.25) → (0,60,33)F`。截面宽 10F、竖向高 15F，朝 +Y 下降，斜率 3/8。

整根预览沿上皮控制线取 120F 长度，以承托控制段中点为中心向两端对称延伸。预览上皮端点约为 `(0,-11.179751,74.692406)F` 和 `(0,101.179751,32.557594)F`。120F 是本项目预览采用的斜线长度，不是水平投影长；端部暂采用等厚平端，未宣称历史昂嘴造型。

下昂仍由 `YFS_DG_ANG_GENERATOR` 生成。预览端点没有写成 Connector，且保留 `endpoint_status=UNRESOLVED_BEAM_INTERACTION`、`preview_endpoint_status=PROJECT_PREVIEW_ONLY_NOT_CONNECTOR`。`OUT_UNRESOLVED` 明确保留一条 `RIDING_BEAM_AND_ANG_TAIL` 接口请求。

## 验证

| 针对性验收 | 结果 |
|---|---|
| 完整性与共享 Atom | PASS：41 固定件 + 1 ANG，13 类共享几何 |
| 模板坐标与竖向层位 | PASS：坐标匹配用户规范；单位缩放，无新增 Atom |
| Connector 与 BBox | PASS：75F／79F 分离；±60F 接口正确 |
| ANG 控制段与预览体分离 | PASS：3/8、120F、承托点正确；梁栿端点仍未解析 |
| Recipe 隔离与 4P 保持 | PASS：4P 为原 21 件及原 BBox；原 5P 仍未解析；切回新 5P 为 42 件 |

工程已保存、重新打开验证；默认 Debug OFF。另附基于真实几何的 OpenGL 预览。未重复历史资料研究、Atom topology QA 或原 Branch/Jump 测试。

新增独立版本：Assembly 1.1、Vertical Solver 1.2、ANG Generator 1.1、Template Atom Assembler 1.0；新 HIP 内嵌所需的全部 7 个 HDA 定义。新 Recipe／Vertical Rules／ANG Presets 使用 v2 文件，原 v1 文件和 Golden 4P HIP/HDA 保持不变。

使用 `Generate 5P Project Assembly` 开关完整 5P；`Generate Ang Preview` 可单独关闭下昂；`Show Debug Guides` 显示项目控制点。输出为 `OUT_5P_FULL_PROJECT`、`OUT_5P_FIXED_ATOMS`、`OUT_5P_CONNECTORS`、`OUT_UNRESOLVED`、`OUT_DEBUG`。导出为 `generated/YFS_M_DG_5P_COLUMNHEAD_PROJECT.bgeo.sc`。

下一步：在该通用项目版基础上，独立定义 `RIDING_BEAM`／骑栿接口和压昂尾条件，再确定昂体真实端点与端部造型；不要将当前对称延伸预览端点升级为历史 Connector。
