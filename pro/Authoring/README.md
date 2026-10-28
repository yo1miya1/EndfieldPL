# SI-1 离线来源与发布

完整操作顺序、工具修改清单和从零采集的现存缺口，以[从 RDC 到 Unity 的详细操作手册](../../doc/learning/rdc-to-unity-tool-workflow.md)为准。本文保留来源与数据格式摘要。

Typhon2 使用单独的 `Extracted/Typhon2` 和 `Tools/Typhon2`，其已有数据迁移与完整发布顺序见 [Typhon2 工具说明](Tools/Typhon2/README.md)。两者共用 Unity 资产发布器与运行 SRP，不能把 SI1 的坐标变换、PNG 颜色边界或 CBuffer 行号直接套到 Typhon2。

Lino1使用同样的分层方式，完整步骤见[Lino1工具说明](Tools/Lino1/README.md)。Typhon2/Lino1共用`capture_materials.py`和`capture_scene_plan.py`，各角色只保留来源映射与薄入口；Lino需要的多层粒子、镜面查表和折射快照已作为共享Shader/Pass功能发布。

`Extracted/SI1` 保存实际截帧导出的网格、贴图、着色器与参数来源；`Tools` 负责离线整理；`Assets/Authoring/Editor` 负责Unity资产发布。运行场景仅引用 `Assets/Endfield` 内的Mesh、Texture、Cubemap、Material、UIComposition与Shader。删除原RDC、Extracted目录和工具后，已经发布的场景仍可运行。

原输入为工作区 `src/SI-1.rdc`，保持只读。本次源SHA-256是 `e2c40a194bf57fe4827aa631a4a50562c792258a2007819d2c1d3f6745ef3bec`。重新回放前须复制到独立ASCII路径（建议 `pro/Authoring/Work/SI1.rdc`）并比较源/副本SHA-256。外部rdc2dcc已先复制到工作区 `tool/rdc2dcc`；仅本地driver增加完整PostVS输出保存，未改外部原工具。

`python -X utf8 pro/Authoring/Tools/prepare_capture_copy.py` 会创建并哈希验证上述独立副本；已存在但哈希不同的副本会拒绝覆盖。`prepare_export_configs.py` 将Tools/ExtractionConfigs内的相对路径模板实例化到Work/ExportConfigs，包含UI、特效driver与native导出参数。背景初次解算、主Source证据汇总、描边VB初采仍有历史一次性步骤，不能视为已具备全自动从零入口。

重新从RDC开始时，先执行复制后的 `tool/rdc2dcc/rdc2blendCppCli.exe run --capture pro/Authoring/Work/SI1.rdc --workspace pro/Authoring/Work/rdc2dcc --task SI1 --component endfield --solver endfield --origin character --json`，再补材质/透明/UI读取。此流程产出原始角色FBX、world2及scene；本次稳定副本已在Extracted/SI1/Source。553完整属性补件由restore_character_submesh.py读取CharacterSupplement/553，不要求tmp。

## 当前资产再生成顺序

现有提取数据未变时，直接在Unity执行 `Endfield/Authoring/Publish SI1 Scene`。需要重新整理语义映射时，在工作区根使用Python的UTF-8模式：

```powershell
python -X utf8 pro/Authoring/Tools/build_semantic_material_bindings.py
python -X utf8 pro/Authoring/Tools/build_semantic_effect_bindings.py
python -X utf8 pro/Authoring/Tools/build_semantic_soft_effect_bindings.py
python -X utf8 pro/Authoring/Tools/build_semantic_layered_bindings.py
python -X utf8 pro/Authoring/Tools/prepare_scene_import.py
```

这些脚本使用已归档Extracted及相应来源证据，不重新回放RDC。随后执行 `Endfield.Editor.EndfieldSceneBuilder.PublishScene()`：它内部重建场景、调用UIBuilder，并再次保存带UI引用的场景。只调用BuildScene再Build UI而不保存，会造成重开/Player缺UI。几何、方向、纹理仅在相应输入变化时重建，详细命令见操作手册。

UI需要重新生成时，必须按 `prepare_ui_geometry.py` → `build_ui_semantic_parameters.py` 配对执行。两步会覆盖 `Assets/Endfield/Shaders/UI`；第二步移除manifest的constants，不能在已语义化结果上独立重复运行。现有UI正确时不把它们列为日常发布步骤。

`CharacterDirections/Native`保存13个必要draw的完整PostVS与基础状态；`prepare_character_directions.py`按顶点数和UV0逐值配对，输出每顶点Nx,Ny,Nz,Tx,Ty,Tz,Tw的源D3D世界方向。`prepare_scene_import.py`从CharacterDirections/import.json接入normalTangentPath；发布器只做(-x,y,-z)，不重复placement，运行仍用当前Unity模型/相机矩阵。眼睛取实际1061 Forward切线，不能把502 GBuffer的motion误读为T。具体误差与未消费T的488例外见doc/validation/geometry-directions.md。

`verify_body_geometry.py`是只读离线核验：用GeometryValidation/538原IB/RDCI与现有538/1019完整PostVS验证位置、索引和阶段pose一致性，不重开RDC、不修改模型。其结果在doc/validation/body538-geometry.json；当前用户可见三角台阶由阴影A/B隔离，不通过RecalculateNormals掩盖。

UI原始采集是 `rdc2blendCppCli read --matex --eid-min 2148 --eid-max 3389`；特效采集范围为1404–1730；背景通过character流程的同一driver显式读取655/673/1210，再以endfield solver解算。所有工具只能打开校验后的独立副本。材质模式是在先完成 `run --origin character` 后补齐，不以matex替代角色居中流程。真实调用与配置索引见 `doc/capture/tool-provenance.json`，原始driver配置随各Read目录保存。

`export_native.py` 在qrenderdoc中读取 `EF_EXPORT_CONFIG`，导出实际PostVS、绑定与固定状态；输出路径由配置给出。输入/输出路径不参与运行时。`decompile_ui_programs.py`、`decompile_effect_programs.py` 使用工作区工具副本中的HLSLDecompiler，仅翻译实际DXBC。

## 数据与方向约定

- `world2`保留源IB次序。FBX writer才额外把三角形 `(a,b,c)` 写成 `(a,c,~b)`。读world2时不能照搬FBX反绕序。切线w保留源符号；是否改变符号应由实际总变换的行列式和光栅正面约定决定，不能无条件取负。
- 世界流为rdc2dcc场景帧：源D3D rebased坐标经过 `F(x,y,z)=(x,-z,y)`。placed=true需先应用scene矩阵，baked=true不重复placement；然后所有对象及相机统一减character origin，再应用主构建器的BlenderToUnity。当前映射 `(-x,z,y)` 的det=+1。
- 真实599手套的4792顶点已经闭环：world2→placement→F逆→源VP 与实际PostVS NDC最大X误差 `6.53e-8`、Y误差 `3.84e-7`。见 `doc/capture/599-postvs-coordinate-check.json`。此前显示左右错误来自旧Renderer GPU缓存，修复记录在 `doc/validation/image-corrections.md`。
- 源UI copy2906仅翻Y，没有X翻转。95个UI draw保留完整VS插值流，15张源图集在Unity导入时恢复D3D行序；临时UI层与camera/backbuffer的Y适配独立于场景坐标。UI shader已拆为93行语义参数，运行没有原始CB数组。映射见 `doc/capture/ui-parameter-mapping.json`。
- 1649是受光衣料叠层，覆盖出最终白色菱纹；同时与shadow424使用同一几何。其法线/切线为实际PostVS o3/o4，UV0与shadow424逐bit相同。其它粒子颜色为实际VS o5；1649无COLOR，不套InkEffect。

## 环境与诊断

Cube11550完整预滤波链位于 `EnvironmentReflection/11550/rgba-float4.bin`，按source face `+X,-X,+Y,-Y,+Z,-Z`→mip0..7→顶行到末行→float32 RGBA排列。`import.json`记录尺寸和hash；离线发布再做Unity坐标变换，保留全部原mip，不调用Apply(true)重生。

重新导出Cube时：设置 `ENDFIELD_ROOT` 为工作区根、`ENDFIELD_SOURCE_CAPTURE` 为校验副本，然后用qrenderdoc的 `--python` 执行 `export_reflection_cube.py`，再用普通Python执行 `decode_reflection_cube.py`。原6个3D SH volume在EnvironmentSH归档；本帧角色的实际分支使用源fallback环境色，不能因资源存在而启用它们。

最终画面、GBuffer和逐draw RT只用于 `doc/capture/reference`、tmp诊断与量化比较。Source后处理LUT20329也是诊断RT，不导入运行。运行使用本帧Unity深度、颜色、灯光与原生ReflectionProbe；UI/soft-particle不回采正在写入的深度附件。

## 纹理与颜色发布边界

实际GPU探针证明RenderDoc SaveTexture对BC7_SRGB导出的PNG已经是解码后的线性数值，不能再因原资源SRGB名称进行第二次解码。599/568/520共九处彩色texel与EXR/PickPixel一致，证据见 `doc/capture/texture-export-color-space.json`。UI与角色发布Texture2D均需linear=true；原SRV格式只保留为来源证据。ShaderLab Color属性的源CB向量同样已是GPU线性数值，当前构建器在SetColor序列化边界编码gamma一次；Vector属性保持原数值。

为避免8位线性PNG损失暗部，当前59张静态2D纹理已导出源mip链，位于 `TexturesNative/index.json` 及各RID目录的 `import.json`、`rgba-half.bin`。blob按mip0..N、小端float16 RGBA、D3D顶行至末行排列，不翻行。Unity用RGBAHalf、linear=true、原mipCount创建Texture2D，LoadRawTextureData读取整个blob，再Apply(false)保留原mip。Cube11550继续使用前述独立全face/mip导出。

再生成高精度纹理：先执行 `prepare_native_texture_plan.py`，设置ENDFIELD_TEXTURE_PLAN为Work/native-texture-plan.json的绝对路径，用qrenderdoc `--python` 执行export_native_texture_mips.py；完成后普通Python执行decode_native_texture_mips.py。原SRV视图、消费者语义、原资源格式、每mip尺寸/偏移及SHA-256均在import.json；EXR为未量化中间来源，不是屏幕RT。
