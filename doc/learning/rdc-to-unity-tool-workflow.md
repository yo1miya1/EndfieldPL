# 从 RDC 提取数据到 Unity 工程：工具改动与操作手册

本文以 **SI-1 的已完成重构工程**为基准，整理于 2026-10-29。以工作区根目录 `.` 为路径基准，Unity 工程根为 `pro/`，原始输入为 `src/SI-1.rdc`，外部工具统一约定放在 `tool/`。本文不依赖具体盘符、用户名或机器安装目录。命令根据实际脚本、配置和已有运行记录整理；文档修改不执行提取、发布或测试。

所有命令都从工作区根目录运行。正文路径默认相对此根目录；明确注明的子目录表、源数据内部路径和Unity API要求的`Assets/...`路径按各自说明解释。Markdown链接保持相对本文位置，以便点击。工具要求绝对路径时，由`$EndfieldRoot`与相对路径在运行时组合，不在示例中写死本机位置。

本仓库未附带原始 RDC 与 `pro/Authoring/Extracted/SI1`。已发布 SI1 场景可直接运行；完整再生成输入需从原工作区的`pro/Authoring/Extracted/SI1`归档恢复到本仓库同一路径，再执行发布。原 RDC 另行恢复；`$EndfieldRoot` 始终设为当前仓库根，而非源工作区。后文历史验证结论仍来自原工作区，复制本身没有重新验收。

这份文档同时说明三件事：外部工具具体改了什么；现有提取数据怎样重新发布为独立 Unity 场景；重新从 RDC 开始时，各类数据怎样获取、哪些步骤仍需要人工整理。**现有 SI-1 数据到 Unity 的发布链已经存在；任意 RDC 到完整工程还不是一键转换。** 新角色需要自己的事件、资源、常量和着色模型映射。

## 1. 先选择要执行的路线

| 目的 | 从哪里开始 | 是否需要 RenderDoc |
| --- | --- | --- |
| 打开当前效果、学习管线、调 Unity 灯光 | Unity Hub 打开 `pro`，打开 `Assets/Endfield/Scenes/SI1.unity` | 否 |
| 已发布资产丢失或需要完整重建，提取数据仍在 | 第 4 节：从现有 `pro/Authoring/Extracted/SI1` 发布 | 否 |
| 某个参数、几何、纹理输入变化 | 第 8～11 节：只重建受影响的数据，再发布 | 仅缺少源证据时需要 |
| 从原始 SI-1.rdc 重新提取 | 第 5 节开始，经过采集、归档、语义整理，再回到第 4 节 | 是 |
| 换另一个角色或另一份截帧 | 第 16 节：建立新的角色数据配置，复用现有管线 | 按已有资料是否完整决定 |

不要为了重新发布一次场景而重复所有采集、诊断和截图。后文的几何验证、阴影隔离、像素探针都是已有问题的排查工具，不是日常发布前的必跑步骤。

## 2. 目录、依赖与数据流

### 2.1 三层数据必须分开

```text
src/SI-1.rdc                         原始截帧，只读
    ↓ 独立副本 + RenderDoc / rdc2dcc
pro/Authoring/Work/                  回放副本、配置实例、DCC 中间结果
    ↓ 将需要保留的原件归档
pro/Authoring/Extracted/SI1/          原始缓冲、Shader、CB、贴图和离线导入计划
    ↓ Python 整理 + Unity Editor 发布
pro/Assets/Endfield/                 真正独立的 Unity 运行资产与管线
```

| 目录 | 内容与责任 |
| --- | --- |
| `src` | 原始 RDC。工具不直接写它 |
| `tool/rdc2dcc` | 复制进工作区的外部工具及本地修改；原安装目录未修改 |
| `pro/Authoring/Tools` | 正式离线 Python 脚本与 `ExtractionConfigs` 配置模板 |
| `pro/Authoring/Extracted/SI1` | 可复用的来源资料；放在 Assets 外，不被 Unity 当运行资源导入 |
| `pro/Authoring/Work` | ASCII 回放副本、生成的配置、临时解算结果 |
| `pro/Assets/Authoring/Editor` | Unity 发布器、命令桥、截图和诊断工具 |
| `pro/Assets/Endfield/{Runtime,Shaders,Editor}` | 通用运行管线、Shader、保留的材质 Inspector/状态设置 |
| `pro/Assets/Endfield/{Content,Settings,Scenes}` | 发布的网格、纹理、材质、Prefab、Volume 配置和场景 |
| `doc` | 工程说明、参数来源、取舍与验收证据 |
| `tmp` | 日志、截图、构建产物、历史一次性脚本。不能成为正常场景的运行依赖 |

工具生成的是资产和配置，**不会从任意 DXBC 自动设计出本工程的通用 SRP**。自定义 GBuffer、光照接口、阴影、后处理、UI 调度及可读 Shader 已在 `Assets/Endfield` 中实现；移植新角色时继续使用这套代码，补充实际需要的模型分支。

### 2.2 版本与工具目录约定

| 依赖 | 工作区相对路径与版本 | 使用范围 |
| --- | --- | --- |
| Unity 6 | `tool/Unity/6000.6.3f1/Editor/Unity.exe`，版本`6000.6.3f1` | 发布、编辑器显示、Player 构建 |
| Unity 包 | Core `17.6.0`，UGUI `2.6.0`，以 `pro/Packages/manifest.json` 为准 | 自定义 SRP 与 UI |
| RenderDoc | `tool/RenderDoc/qrenderdoc.exe`，已使用版本v1.46 | 原生回放，提供内置 Python 的 `renderdoc` 模块 |
| rdc2dcc 本地副本 | `tool/rdc2dcc/rdc2blendCppCli.exe` | character 流程；程序名实际是 rdc2blendCppCli |
| 普通 Python | `tool/Python/python.exe`，64位Python 3.11或更高，安装NumPy/Pillow | 离线几何、语义和纹理解码；Pillow 用于图像预览/比较 |
| MCP 后端 | `tool/renderdoc-mcp/bin/renderdoc-mcp.exe` | Shader/CB/绑定等交互式批次采集；旁边需匹配的依赖 DLL |
| HLSLDecompiler | `tool/rdc2dcc/SI1Scripts/HLSLDecompiler.dll` | Windows ctypes 反编译实际 DXBC |

上表是本文的工具部署约定，按对应目录安装或放置完整依赖；不表示所有工具都已随仓库分发。MCP后端通过`--exe`或`RENDERDOC_MCP_EXE`显式指定。`qrenderdoc + export_native.py` 路线不依赖 MCP 服务。普通 Python 不等于 qrenderdoc 内置 Python：含 `import renderdoc` 的导出脚本必须交给 qrenderdoc。Unity 发布读取 world2，不要求安装 Blender；只有另行编辑 `.blend` 才需要 Blender。

在工作区根目录打开PowerShell，后文示例统一先设置；新开终端也使用此根目录并执行这段初始化：

```powershell
$EndfieldRoot = (Get-Location).Path
$UnityExe = Join-Path $EndfieldRoot 'tool/Unity/6000.6.3f1/Editor/Unity.exe'
$RenderDocExe = Join-Path $EndfieldRoot 'tool/RenderDoc/qrenderdoc.exe'
$PythonExe = Join-Path $EndfieldRoot 'tool/Python/python.exe'
$RenderDocMcpExe = Join-Path $EndfieldRoot 'tool/renderdoc-mcp/bin/renderdoc-mcp.exe'
$ProjectPath = Join-Path $EndfieldRoot 'pro'
New-Item -ItemType Directory -Force -Path "$EndfieldRoot/tmp/unity" | Out-Null
```

Python 命令使用 `-X utf8`，避免本机中文编码影响记录。普通 prepare/build/decode 脚本主要按自身位置推导工作区，不提供统一 `--capture/--out` 参数；不要给它们套用不存在的参数。

## 3. 本轮究竟改了哪些工具

### 3.1 外部 rdc2dcc：只有一个核心文件改动

原始rdc2dcc发行目录先完整复制到`tool/rdc2dcc`，只修改工作区副本。对核心27个文件的比较显示，只有 **`tool/rdc2dcc/env/rdc_driver.py`** 不同；C++ CLI、solver、组件配置、FBX writer等未修改。

原工具角色读取流程已经调用`GetPostVSData(..., VSOut)`取得输出缓冲信息，再以`GetBufferData`把所需顶点范围的完整packed PostVS读入`praw`；后续`posed`只取每个顶点开头的`float4`位置。本轮在两者之间增加一行，将已读取的完整字节保存下来：

```python
praw = bytes(controller.GetBufferData(md.vertexResourceId,
    int(md.vertexByteOffset), pstride * need))
save(os.path.join(d, "postvs.bin"), praw)  # 新增
```

这使首次角色筛选漏掉的553 draw可以结合真实VS输出布局恢复position/UV/normal/tangent。**没有重写solver或蒙皮算法，也没有重新编译rdc2dcc核心DLL/可执行文件**；方向修复发生在后面的离线补充脚本。文件原/改版hash与首次命令记录于[tool-provenance.json](../capture/tool-provenance.json)。

通用性分为两层：保存原始PostVS字节不依赖角色名、EID或固定属性布局，可复用在能够由RenderDoc取得VS输出的其他绘制；将字节解释成法线、切线、UV等属性，则必须结合各Shader的输出签名、stride、索引和坐标约定。单独一个bin不能自动恢复所有模型语义。

当前补丁仅加在角色流程`WANT_MESH`分支；原工具Matex的`_mesh_dump`也读取`praw`，但本轮没有给该分支添加相同落盘行。实例/阶段选择仍沿用原工具逻辑，因此不能声称所有流程、全部实例或后续几何阶段都已统一导出。需要扩为公共能力时，应让相关分支共用原始输出保存逻辑，并同时记录布局、索引、实例和阶段信息；这属于后续工具改造，本轮尚未实施。

`tool/rdc2dcc/SI1Scripts`是另加的早期工作脚本和DLL。`HLSLDecompiler.dll`是旧工程已有的DXBC反编译依赖，本地文件与旧工程文件SHA-256相同，原样复用，不是本轮编译产物。除当前decompiler依赖外，里面的 `complete553.py`、`prepare-ui.py` 等不应当成最新入口：部分仍写旧目录或读取 tmp。正式入口位于 `pro/Authoring/Tools`。


2026-10-29已将该定制版以独立文件`rdc_driver_endfield.py`合入rdc2dcc源码的`env/`。以rdc2dcc源码仓库根为基准，位置为`rdc2blendCpp-cli/rdc2blendCpp/env/rdc_driver_endfield.py`；原`rdc_driver.py`保留。新增文件与本工作区定制副本内容一致，现有工程的`CopyEnv`会随其他env文件一起复制它，无需新增C++接口。

CLI仍默认选择通用`rdc_driver.py`。在含定制文件的发行目录运行时，用`--driver env/rdc_driver_endfield.py --package-name rdc2blend_env`显式选择；若把发行目录放在本文约定的`tool/rdc2dcc`下，则从工作区根传`--driver "$EndfieldRoot/tool/rdc2dcc/env/rdc_driver_endfield.py"`。本次只加入源码文件，没有重新编译或更新已有发行目录，因此不把文件改名误写成默认选择已经切换。

### 3.2 从旧工程或技能复用的工具

| 工具 | 复用与本轮改动 |
| --- | --- |
| `pro/Authoring/Tools/export_native.py` | 基于旧工程 `pro/Generation/Tools/frame_analysis/export_native.py`；新增六类能力，见下表 |
| `pro/Authoring/Tools/frame_analysis/{rdc_analyze,rdc_probe,mcp_client}.py` | 从 renderdoc-frame-analysis 技能复制，代码未修改；持久保存到工程中 |
| `pro/Authoring/Tools/read_exr.py` | 旧工程原样复用；只支持本流程的未压缩 scanline EXR，不是任意 EXR 解码器 |
| `tool/rdc2dcc/SI1Scripts/HLSLDecompiler.dll` | 旧工程原样复用；不是本轮编写的反编译器 |

`export_native.py` 的本轮增量：

| 增量 | 解决的问题 |
| --- | --- |
| `pixelProbes` | 用实际 PickPixel 判断导出 PNG 的颜色编码，避免第二次 sRGB 解码 |
| `characterShadowAudit` | 摘取本轮角色阴影 map/caster/receiver、GB2 和程序证据；包含 SI1 专用条件，不是通用角色识别 |
| `ignoreMarkerPop` | 在标记结束事件附近选择实际绘制状态 |
| `...AllMarkers` | 读取所有同名 marker，避免只取最后一个阶段 |
| `graphicsPrograms` | 保存真实 VS/PS DXBC |
| `graphicsConstantLayouts` | 保存反射变量布局和偏移，便于解释 CB 原始字节 |

PostVS、普通绑定、纹理、compute、buffer 导出及回放关闭机制原来就有，不应全部记成本轮新增。

### 3.3 新增的工程离线转换工具

以下文件均位于 `pro/Authoring/Tools`。它们是实际证据与 Unity 资产之间的转换层，包含 SI1 的映射规则。

| 工具 | 输入 → 输出 | 本轮用途 |
| --- | --- | --- |
| `prepare_capture_copy.py` | `src/SI-1.rdc` → `pro/Authoring/Work/SI1.rdc`、完整性记录 | 独立 ASCII 工作副本；固定本份 SI1 hash |
| `prepare_export_configs.py` | 模板 `{ROOT}` → `pro/Authoring/Work/ExportConfigs` | 路径从早期本机 tmp 改为工作区配置 |
| `restore_character_submesh.py` | `CharacterSupplement/553` → world2、manifest、scene 条目 | 恢复漏件；**不生成新的 FBX** |
| `prepare_character_directions.py` | 真实 PostVS → `CharacterDirections` float7/import | 恢复已 pose 的 N/T；眼睛取 Forward 真切线 |
| `prepare_outline_stream.py` | 617 原 VB1 与 world2 → 描边流证据 | 核对 TS2N；运行直接读 world2 中已有的 flags2 流 |
| `prepare_background.py` | 已有台面 world2、673 PostVS、1210 参数 → Background/import | 修正台面 UV，为接收动态阴影生成台面几何法线 |
| `prepare_effect_geometry.py` | EffectsRead/Native、源 VP → Effects/world2、UV、颜色 | 当前 pose 的真实 FX 几何；1649 保留受光 N/T |
| `decompile_{effect,ui}_programs.py` | 真实 DXBC → HLSL 与索引 | 程序理解与语义映射；不自动得到可发布的通用 Shader |
| `build_semantic_material_bindings.py` | 主角色 CB/绑定 → 主材质与场景语义配置 | 明确参数名、纹理槽、keyword、渲染状态和初始灯光 |
| `build_semantic_effect_bindings.py` | FX CB/程序/绑定 → 七类主要效果项 | 墨带、覆盖层等实际启用分支 |
| `build_semantic_soft_effect_bindings.py` | 前一步结果与 1693/1730 输入 → 追加软效果 | 依赖前一步已经生成的 effect map |
| `build_semantic_layered_bindings.py` | 1649 真实输入 → 独立衣料叠层语义 | 白色菱纹来自受光叠层，不是修改基础色贴图 |
| `prepare_ui_geometry.py` | UIRead/Native/Programs → UIPrepared、UI Shader | 95 draw 的实际顶点、固定状态和临时常量接口 |
| `build_ui_semantic_parameters.py` | 上一步结果 → UI 命名参数与 Shader 属性 | 替换原 CB 行协议；必须与上一步配对执行 |
| `prepare_native_texture_plan.py` | 语义纹理消费者与 SRV → 全 mip 导出计划 | 只选择实际静态纹理，排除帧 RT |
| `export_native_texture_mips.py` | RDC 静态 2D → 全 mip EXR | 保留 GPU 解码值、alpha 和源 mip |
| `decode_native_texture_mips.py` | EXR → RGBAHalf blob/import/index | Unity 原生纹理发布输入 |
| `export_reflection_cube.py` / `decode_reflection_cube.py` | 11550 六面全 mip → HDR blob/import | 保留预滤波 Cube，而非单层 PNG |
| `prepare_scene_import.py` | 上述各类数据 → `Source/scene-import.json` | 所有来源在此汇合，Unity 只读清晰的导入计划 |
| `verify_body_geometry.py` / `verify_body_shadow_normals.py` | 已归档 538 数据 → 诊断报告 | 定位已发生的皮肤问题，不是生成流程的一部分 |

### 3.4 Unity 发布与验收工具的改动

这些工具位于 `pro/Assets/Authoring/Editor`，Editor 专用，不进入 Player。

| 文件/工具 | 主要职责与修复 |
| --- | --- |
| `EndfieldSceneBuilder` | world2/语义计划发布为独立 Mesh、Material、Texture、Prefab、场景；统一坐标；正确处理 Color 与线性纹理；更新已有资产时显式上传 GPU 数据 |
| `SI1UIBuilder` | 发布 UI Mesh/材质/图集/Composition，按用途命名并保留 GUID；更新 Mesh GPU 流；相机引用需要保存场景 |
| `EndfieldSceneBuilder.PublishScene` | 将 BuildScene、Build UI、再次保存场景合成正式完整入口，解决当前窗口有 UI、重开或 Player 丢 UI |
| `EndfieldReflectionBuilder` | 全 face/mip HDR Cubemap 与原生 ReflectionProbe 发布，坐标转换集中在一个边界 |
| `EndfieldPostProcessBuilder` | 建立 VolumeProfile、关联管线 Shader；原时序算法未完整复刻，不能称算法等价 |
| `EndfieldCharacterShadowAuthoring` | 把源 shadow profile 固化为可读组件；按实际材质和投影设置建立 receiver/caster 列表 |
| `EndfieldEditorBridge` | 文件队列执行刷新、公开静态入口、开场景、取证、退出；退出先回执再 Exit，不依赖后台可能不执行的 delayCall |
| `EndfieldFrameCapture` | 相机截图和 RDC；Begin/End 两侧通过 ReadPixels 同步，解决只截到后处理尾段的问题 |
| `EndfieldGameViewCapture` | 单独读取真实 GameView 内部 RT，区别于临时 Camera.Render 截图 |
| `EndfieldLightingDemoBuilder` / `EndfieldLightingStudy` | 原生方向/点/聚光示例、独立场景和按灯隔离截图 |
| `EndfieldVisualDiagnostics`、`EndfieldShadowDiagnostics`、`EndfieldShadowBiasStudy`、`EndfieldReflectionDiagnostics` | 记录机位、阴影隔离、反射取证；按实际问题调用 |
| `EndfieldPublicationCleanup` | 按场景/Prefab/Settings 依赖归档被替代的发布资产，保存 meta 与记录 |

运行时 UI 的 Y 翻转、角色局部阴影、描边调度等属于**管线修复**，不是提取器改动。参见 [管线设计](../rendering/pipeline-design.md)、[角色阴影](../rendering/character-shadows.md) 和 [UI 方向](../validation/ui-game-view-orientation.md)。

## 4. 路线 A：从现有 SI1 归档重新生成 Unity 资产

### 4.1 现有数据已经包括什么

当前 `pro/Authoring/Extracted/SI1` 包含 Source、CharacterSupplement、CharacterDirections、Background、EffectsRead/Native/Programs、UINative/UIRead/UIPrograms/UIPrepared、TexturesNative、EnvironmentReflection、Outline、ShadowReceiverNative 等目录。

整理时的状态为：最终 `scene-import.json` 有 22 个部件；静态 2D 原生 mip 链 59 张；UI 有 95 个 draw、7 个 Shader 家族、15 张静态图集；反射 Cube 有 6 面、8 mip。数量只是 SI1 当前记录，不是新角色必须满足的标准。

如果导入计划和提取数据未变化，直接执行第 4.3 节即可。需要重新整理材质映射时，执行下面的最小链。

### 4.2 重新生成语义与导入计划

```powershell
& $PythonExe -X utf8 pro/Authoring/Tools/build_semantic_material_bindings.py
& $PythonExe -X utf8 pro/Authoring/Tools/build_semantic_effect_bindings.py
& $PythonExe -X utf8 pro/Authoring/Tools/build_semantic_soft_effect_bindings.py
& $PythonExe -X utf8 pro/Authoring/Tools/build_semantic_layered_bindings.py
& $PythonExe -X utf8 pro/Authoring/Tools/prepare_scene_import.py
```

主材质脚本同时生成 `semantic-scene-settings.json`，包含灯光/环境初值和角色阴影 profile。效果脚本之间有先后依赖，soft 脚本不能放到主 effect 脚本前面。几何、方向、原生纹理和 UI 资料未改时，不需要重新生成它们。

这些 Python 命令只生成 JSON/离线数据，不会生成 Unity `.mat`、`.asset`、`.unity`。下一步才是 Unity 发布。

### 4.3 Unity 中完整发布

在 Unity 6000.6.3f1 打开 `pro`，使用菜单：

**`Endfield → Authoring → Publish SI1 Scene`**

对应完整方法：`Endfield.Editor.EndfieldSceneBuilder.PublishScene`。

该入口依次：

1. 读取 `pro/Authoring/Extracted/SI1/Source/scene-import.json`。
2. 创建/更新已发布网格、材质、贴图、环境反射、角色与效果 Prefab。
3. 重建 SI1 场景、Unity 相机/Light、Volume、管线配置。
4. 创建 UIComposition，绑定到场景相机。
5. **再次保存 SI1 场景**，使 UI 引用在重开和构建后仍存在。

全量发布会重建生成场景，并重新写入材质参数及项目的相关渲染设置。已有 GUID 尽量保留，但不意味着用户在生成资产上手调的值会保留。需要长期保留自行摆放的场景时，另存自己的场景再使用这些 Prefab。

同一工程未被其他 Unity 实例打开时，也可以批处理：

```powershell
& $UnityExe -batchmode -quit -accept-apiupdate `
  -projectPath $ProjectPath `
  -executeMethod Endfield.Editor.EndfieldSceneBuilder.PublishScene `
  -logFile "$EndfieldRoot/tmp/unity/publish.log"
```

若编辑器已经打开，用菜单或第 12 节的桥接，不能再启动同一个工程的第二个 batch 实例。这里不要加 `-nographics`。等待当前命令结束后才执行依赖它的下一步。

### 4.4 发布结果与构建

| 输出 | 位置（相对 `pro/Assets/Endfield`） |
| --- | --- |
| 角色、环境、效果 Mesh/Material/Texture | `Content/SI1/{Meshes,Materials,Textures}` |
| 角色、环境、效果 Prefab | `Content/SI1/Prefabs/{SI1,Environment,CharacterEffects}.prefab` |
| UI 数据 | `Content/SI1/UI`，包括 `UIComposition_SI1.asset` |
| 管线与后处理配置 | `Settings/EndfieldPipeline.asset`、`EndfieldPostProcess.asset` 等 |
| 正式效果场景 | `Scenes/SI1.unity` |

构建菜单为 `Endfield → Build → Windows player`；命令为：

```powershell
& $UnityExe -batchmode -quit -accept-apiupdate `
  -projectPath $ProjectPath `
  -executeMethod Endfield.Editor.EndfieldSceneBuilder.BuildPlayer `
  -logFile "$EndfieldRoot/tmp/unity/player-build.log"
```

需要安装 Windows64 Build Support。输出 `tmp/build/Windows/EndfieldRebuild.exe`，构建记录 `tmp/unity/player-build.txt`。**BuildPlayer 只构建磁盘上已保存的 SI1，不会自动 Publish，也不会自动补 UI。** 当前入口不包含两个 MultiLight 示例场景。

## 5. 路线 B：从原始 RDC 开始

### 5.1 建立回放副本

```powershell
& $PythonExe -X utf8 pro/Authoring/Tools/prepare_capture_copy.py
& $PythonExe -X utf8 pro/Authoring/Tools/prepare_export_configs.py
```

第一条从 `src/SI-1.rdc` 创建独立的 `pro/Authoring/Work/SI1.rdc`，记录 `capture-integrity.json`。本份源文件为 313,257,758 字节，SHA-256 为：

```text
e2c40a194bf57fe4827aa631a4a50562c792258a2007819d2c1d3f6745ef3bec
```

脚本针对这份 SI1 固定 hash；不同 RDC 不能直接替换文件名绕过配置。工作副本路径保持 ASCII，不直接对 src 开展会写出旁文件的工具流程。第二条只展开路径模板，不会开始回放。

### 5.2 先运行 character 流程

```powershell
& "$EndfieldRoot/tool/rdc2dcc/rdc2blendCppCli.exe" run `
  --capture "$EndfieldRoot/pro/Authoring/Work/SI1.rdc" `
  --workspace "$EndfieldRoot/pro/Authoring/Work/rdc2dcc" `
  --task SI1 --component endfield --solver endfield `
  --origin character --json
```

`--origin character` 是关键：所有部件按角色中心采用统一原点。后面的 `matex` 负责补读材质和逐 draw 数据，不替代角色流程。

实际输出根在 `pro/Authoring/Work/rdc2dcc/imi/SI1`，不是把 `bin/SI1` 当作模型目录：

| 阶段 | 主要输出 |
| --- | --- |
| read | `read/{survey,camera,collect_config}.json`、`read/raw` |
| parse | `parse/stage.json` |
| solve | `solve/world2/manifest.json` 和 `eid-*.world2` |
| emit | `emit/scene.rdc2scene`、`emit/fbx`、`emit/stage.json` |
| handoff | `pro/Authoring/Work/rdc2dcc/bin/SI1/handoff.json`，记录阶段与相对产物 |

把需要保留的 solve/world2、emit/fbx、scene.rdc2scene、stage.json 归档到 `pro/Authoring/Extracted/SI1/Source` 的对应位置。现有 Source 已经经过补件与修正；重新发射的初始结果不能被当成最终等价结果，必须继续完成相关补充步骤。

`Source/capture-camera.json` 保存源 VP、frame、unit_scale 和变换约定，供 FX 逆投影等离线处理使用。它的首次建立目前仍来自初始流程的人工整理，**没有统一的持久生成入口**；新 capture 需要从实际 read/parse 的相机与矩阵结果建立，不能继承 SI1 的 VP。

### 5.3 不必把全部 API 都采一遍

已完成项目的证据优先复用。新 capture 先定位角色 GBuffer/表面受光、阴影、透明/FX、后处理和 UI 的实际事件；记录每个目标的几何、程序、绑定、常量和固定状态，再选择导出。没有 marker 时依靠实际 MRT、深度、程序和资源关系确定阶段，不靠画面命名猜测。

同一目标使用一个串行回放会话。qrenderdoc 导出也应等上一进程结束再执行下一份配置。脚本退出码和输出 `errors/ok` 表达的是对应采集结果，不等于最终 Unity 效果已经验证。

## 6. 用 MCP 获取 Shader、常量和资源绑定

### 6.1 启动持久会话

在一个 PowerShell 窗口运行：

```powershell
& $PythonExe -X utf8 pro/Authoring/Tools/frame_analysis/rdc_probe.py serve `
  --dir "$EndfieldRoot/pro/Authoring/Work/MCP-SI1" `
  --exe $RenderDocMcpExe `
  --idle-timeout 1800
```

该进程保持运行；另一个窗口向 `pro/Authoring/Work/MCP-SI1/jobs` 写请求。启动后产生 `tools.json` 和 `ready.json`。以后端实际 schema 为准，脚本头部旧版本/工具数注释不代表当前服务版本。

第一批请求示例，在另一个已初始化的终端执行。capture路径由工作区根动态生成，请求以UTF-8保存到`pro/Authoring/Work/MCP-SI1/jobs/001.request.json`：

```powershell
$capturePath = Join-Path $EndfieldRoot 'pro/Authoring/Work/SI1.rdc'
$requests = @(
    @{ name = 'open_capture'; args = @{ path = $capturePath } }
    @{ name = 'get_pipeline_state'; args = @{ eventId = 585 } }
    @{ name = 'get_bindings'; args = @{ eventId = 585 } }
    @{ name = 'get_shader'; args = @{ eventId = 585; stage = 'ps'; mode = 'disasm' } }
    @{ name = 'list_cbuffers'; args = @{ eventId = 585; stage = 'ps' } }
)
$jobDirectory = Join-Path $EndfieldRoot 'pro/Authoring/Work/MCP-SI1/jobs'
New-Item -ItemType Directory -Force -Path $jobDirectory | Out-Null
$pendingPath = Join-Path $jobDirectory '001.tmp'
$requestPath = Join-Path $jobDirectory '001.request.json'
$json = ConvertTo-Json -InputObject $requests -Depth 8
[System.IO.File]::WriteAllText($pendingPath, $json, [System.Text.UTF8Encoding]::new($false))
Move-Item -LiteralPath $pendingPath -Destination $requestPath
```

根据返回的 CB 列表和真实绑定，再写下一批；以下 index/RID 是本流程的请求形态示例：

```json
[
  {"name":"get_cbuffer_contents","args":{"eventId":585,"stage":"ps","index":0}},
  {"name":"goto_event","args":{"eventId":585}},
  {"name":"export_texture","args":{"resourceId":"ResourceId::95727","mip":0,"layer":0}}
]
```

`index` 从 `list_cbuffers` 取，不能直接用 shader 的 bindSlot 代替。需要 VS/PS 等阶段时分别读取；用于源灯光、材质、实例的常量页各自保留。纹理 RID 只在当前 capture 内有意义。

写队列文件时，先写 `.tmp`，写完后重命名成 `.request.json`，避免服务读到半个 JSON。每批等待对应结果再发依赖批次。`rdc_probe` 的结果名是 **`001.request.result.json`**，与 Unity 桥接的命名不同。`raw` 保存每次完整返回，export 同时归档到 `artifacts` 并追加 `assets.jsonl`。

结束请求：

```json
[
  {"name":"close_capture","args":{}},
  {"name":"session_status","args":{}},
  {"name":"__stop__"}
]
```

服务 finally 也会尝试关闭 capture，随后落盘 `closed.json`。

### 6.2 采集原件怎样变成 Source

原 SI1 会话采集了逐 draw 的 pipeline/bindings、Shader 和 CB 内容。正式来源格式为：

| 原始返回 | 稳定归档格式 |
| --- | --- |
| `get_pipeline_state` + `get_bindings` | `Source/material-bindings.json`，`materials:[{eid,pipeline,stages}]`；纹理 readOnlyResources 关联 texturePath |
| `get_cbuffer_contents.result` | `Source/Constants/{eventId}_{stage}_cb{index}.json`，保存 eventId、stage、bindSlot、variables |
| `get_shader.result.disassembly` | `Source/Shaders/{eventId}_{stage}.txt` |
| `export_texture` | `Textures/tex_<RID>.png`，保留采集来源；最终静态材质优先使用完整高精度 mip 链 |
| 文件来源记录 | source-manifest：来源、相对路径、尺寸、hash；旧 manifest 是历史快照，不是当前全目录的最新索引 |

**当前自动化缺口：** 最初汇总器仍是 `tmp/capture/publish.py`，内部写早期 `Assets/Endfield/Content/SI1/{Source,Textures}`。它没有迁移成正式 Tools 入口，不能原样运行。当前归档已经齐全，可以直接用于路线 A；若从空目录重提，需要按上表整理，或先把这个 publisher 的输入会话与输出路径改成新的稳定位置并保存为正式工具。

这一步是“归档实际结果”，不是让生成器猜参数名称。先确保事件、槽位、类型、数值来源可追溯，再进入第 9 节的语义映射。

## 7. 原生 PostVS、UI/FX 与阴影补采

### 7.1 三种配置不要混用

| 执行脚本 | 配置环境变量 | 配置用途 |
| --- | --- | --- |
| `tool/rdc2dcc/env/rdc_driver.py` | `RDC2BLEND_TASK` | rdc2dcc driver 的逐 draw/Matex 读取 |
| `pro/Authoring/Tools/export_native.py` | `EF_EXPORT_CONFIG` | 原生状态、PostVS、CB、程序、buffer/texture |
| `pro/Authoring/Tools/export_native_texture_mips.py` | `ENDFIELD_TEXTURE_PLAN` | 已整理静态纹理的完整 mip 链 |

示例：

```powershell
$env:EF_EXPORT_CONFIG = "$EndfieldRoot/pro/Authoring/Work/ExportConfigs/character-directions.json"
& $RenderDocExe --python "$EndfieldRoot/pro/Authoring/Tools/export_native.py"
```

配置由第 5.1 节生成到 Work；需要调整来源时编辑正式 `pro/Authoring/Tools/ExtractionConfigs` 模板，再展开，避免只改即将被覆盖的 Work 文件。

### 7.2 当前模板的真实用途

| 模板 | 输出与采集内容 |
| --- | --- |
| `character-directions.json` | CharacterDirections/Native；13 个 PostVS，包括眼睛 Forward1061、身体 Forward1019，及基础状态/绑定 |
| `effects-native.json` | EffectsNative；FX 的 PostVS、状态、绑定 |
| `ui-native.json` | UINative；95 个 UI PostVS，状态/绑定另含 copy 合成事件 |
| `shadow-receiver.json` | ShadowReceiverNative；372/903/914 的状态、原 CB、布局、DXBC、绑定 |
| `shadow424.json` | 424/635 固定状态的定向证据，输出 Work |
| `shadow424-uv.json` | 424 PostVS 等定向证据；不能替代完整 Cube 导出 |
| `sh-volume.json` | 六个真实 3D volume 原件；本帧实际分支未启用它们 |
| `outline635.json` | **目前只含 capture/output/skipCompute，未配置实际 VB/纹理采集项**，不能靠运行此模板重建描边原件 |
| `EffectsRead-driver.json` | rdc_driver 配置，范围 1404～1730，输出 EffectsRead |
| `UIRead-driver.json` | rdc_driver 配置，范围 2148～3389，输出 UIRead |

没有正式的 `BackgroundRead-driver.json` 模板。现有 BackgroundRead 可复用；从零生成的历史配置/solve 在 tmp 中，见第 17 节。

### 7.3 UI 和 FX 还需要 Matex 原始读取

```powershell
$env:RDC2BLEND_TASK = "$EndfieldRoot/pro/Authoring/Work/ExportConfigs/EffectsRead-driver.json"
& $RenderDocExe --python "$EndfieldRoot/tool/rdc2dcc/env/rdc_driver.py"

$env:RDC2BLEND_TASK = "$EndfieldRoot/pro/Authoring/Work/ExportConfigs/UIRead-driver.json"
& $RenderDocExe --python "$EndfieldRoot/tool/rdc2dcc/env/rdc_driver.py"
```

每次等待结束。模板启用 `matex=true`，得到 `raw/mat/eid-N/draw.json`、inputs.bin、实际 DXBC、`cb-ps-N.bin`、纹理等。配置中 `textures=false` 控制 scene 路径，不代表 Matex 第二条路径没有纹理。

分别用 `effects-native.json` 和 `ui-native.json` 取得原生补充后，再反编译：

```powershell
& $PythonExe -X utf8 pro/Authoring/Tools/decompile_effect_programs.py
& $PythonExe -X utf8 pro/Authoring/Tools/decompile_ui_programs.py
```

输出 EffectsPrograms/UIPrograms 的 HLSL 和索引。它们用来确认公式、槽位和启用分支；真正运行代码仍需要按 Unity 接口整理。ShadowReceiverNative 当前已归档的 HLSL 也是补充资料，`export_native` 只导 DXBC，不会自动产生这些 HLSL。

## 8. 几何整理：位置、方向、描边和 FX 分开处理

### 8.1 当前已有原件的重建命令

只执行确需重建的项：

```powershell
# Source 基础几何重新提取且缺少 553 时使用。
& $PythonExe -X utf8 pro/Authoring/Tools/restore_character_submesh.py
# 从已归档 PostVS 生成角色真实已 pose 方向。
& $PythonExe -X utf8 pro/Authoring/Tools/prepare_character_directions.py
# FX 几何与原始 varying。
& $PythonExe -X utf8 pro/Authoring/Tools/prepare_effect_geometry.py
# 台面 UV、几何法线、材质输入。
& $PythonExe -X utf8 pro/Authoring/Tools/prepare_background.py
# 核对已保存描边流；不是从 RDC 自动补采 VB。
& $PythonExe -X utf8 pro/Authoring/Tools/prepare_outline_stream.py
```

这些生成器读取 `pro/Authoring/Extracted/SI1`，不会重新打开 RDC。之后重跑受影响的语义脚本和 `prepare_scene_import.py`。

### 8.2 必须保留的方向约定

- world2 保留原始 IB 次序；FBX writer 另作 `(a,b,c) → (a,c,~b)`，不能把 FBX 的规则套到 world2。
- 源 D3D 到 rdc2dcc 场景帧为 `F(x,y,z)=(x,-z,y)`。按照 placed/baked 标记处理 placement，再统一减 character origin。
- SceneBuilder 的场景帧到 Unity 变换为 `B(x,y,z)=(-x,z,y)`，行列式为正。不要无条件反转所有三角形或切线 w。
- 补充 float7 存的是源 D3D 世界空间、已经 pose 的 `[Nx,Ny,Nz,Tx,Ty,Tz,Tw]`；发布时仅转换 `(-x,y,-z)`，不再重复 placement。运行时继续使用当前 Unity 物体矩阵。
- 方向配对按实际顶点数量、UV 和 signature 的 compCount，不能假设每个输出寄存器都是固定 16 字节。

眼睛 502 的 GBuffer VS 没有需要的切线，o4 是 motion；实际 T 来自同几何的 Forward1061。把 motion 当切线会导致视差错位。488 没有可消费的 T，当前材质也不用它，保留原 T 并记录此例外。

身体皮肤的割裂不能统一用 `RecalculateNormals` 掩盖：本轮既修正过 N/T，也修复了独立角色阴影 receiver/filter。最新侧胸台阶的修复没有改变位置/索引。分别见 [几何方向](../validation/geometry-directions.md)、[皮肤与眼睛](../validation/skin-eye-corrections.md)。

### 8.3 描边和受光覆盖层

617 与描边635共享几何。源 VB1 stride12，offset8 为 SNORM8×4 的 TS2N 编码；world2 flags2 已带相同流。prepare_outline_stream 负责核对和归档，Unity 从 world2 读取到 UV2。它不会在缺失的 world2 上自动造一个平均法线流。

1649 是白色菱纹受光衣料叠层，使用真实 N/T 与材质，不是普通墨带。FX 脚本从真实 clip 和源 VP 逆解静态姿态位置，保存 UV/颜色等插值数据，运行时仍由当前 Unity 相机重新投影。原始 capture 只提供当前 pose，不因此恢复骨骼动画。

## 9. 从 CBuffer 到可读材质参数

### 9.1 三类数值分别处理

| 源数据 | 最终落点 | 运行时来源 |
| --- | --- | --- |
| 基础色、法线强度、眼睛视差、材质遮罩等 | 命名 Material 属性、纹理、keyword | Unity Material |
| 混合、剔除、ZTest/ZWrite、队列、stencil 等 | 材质/Pass 状态 | 当前材质与 renderer 调度 |
| 相机、光源、视线、世界法线、阴影矩阵 | 原值只用于初始化场景/理解公式 | 当前 Unity Camera、Light、Transform、动态 shadow map/Probe |

因此，源 CB 只在离线阶段解码，不作为运行 Shader 的原始数组协议。场景初始灯光可以来自捕获值，但之后由可编辑的 Unity Light 驱动。

### 9.2 当前 SI1 映射示例

主材质脚本包含已证实的 GBuffer → 表面受光配对：

```text
488→1040  502→1061  520→997  538→1019  553→1082
568→1101  585→1122  599→1143  617→1165
```

例如 `_NormalScale` 对应材质 `M[0].w`；`_BaseColor` 对应 `M[6]`；普通 `_Roughness = 1 - Forward M[0].x`。这里的 M 要按具体程序的真实 bindSlot 理解，不能跨所有 Shader 套同一个 CB 页。源 mask 的通道按实际采样计算解释，不默认是 Unity 标准金属/粗糙度/AO 打包。

完整参数名称、来源表达式和置信边界见 [shading-models.md](../rendering/shading-models.md)，UI 的 93 行语义映射见 [ui-parameter-mapping.json](../capture/ui-parameter-mapping.json)。生成 JSON 主要包含 `keywords/scalars/vectors/textures` 等，发布器把它们写成正常材质。

### 9.3 角色阴影参数的发布

`shadow-receiver.json` 得到 372 caster 与 903/914 receiver 证据。当前角色 profile 从实际值映射为 1024 tile、receiver depth/normal bias 3/6 texel、filter radius 4 texel、caster depth/slope 8/0。源914使用 GBuffer 扰动法线；903 的面法线分支不能冒充同一公式。

场景发布建立 `EndfieldCharacterShadow` 分组，运行根据当前 Light 与角色 bounds 计算投影和 worldTexel。只有需要更新已有场景的角色阴影配置、保留机位和几何时，使用菜单 `Endfield/Authoring/Publish character shadow settings`。它会更新活动场景中 `SI-1 Character` 根对象及 SI1.prefab，并保存活动场景，不会自动打开 SI1。

## 10. 高精度静态纹理与环境反射

### 10.1 2D 全 mip 链

在主材质、FX、叠层语义绑定齐备后：

```powershell
& $PythonExe -X utf8 pro/Authoring/Tools/prepare_native_texture_plan.py
$env:ENDFIELD_TEXTURE_PLAN = "$EndfieldRoot/pro/Authoring/Work/native-texture-plan.json"
& $RenderDocExe --python "$EndfieldRoot/pro/Authoring/Tools/export_native_texture_mips.py"
& $PythonExe -X utf8 pro/Authoring/Tools/decode_native_texture_mips.py
& $PythonExe -X utf8 pro/Authoring/Tools/prepare_scene_import.py
```

plan 从真实 SRV 与语义消费者选资源，补上本帧平台/背景/描边静态资源。导出器在实际消费者事件读取各 mip，保存未量化 EXR；只接受静态 Texture2D，cube/array/3D 另走对应路径。

每个 RID 输出 `TexturesNative/<RID>/import.json`、`rgba-half.bin` 及 EXR；总表为 `TexturesNative/index.json`。blob 顺序为 **mip0…N → D3D 顶行到末行 → x → little-endian float16 RGBA**。Unity 创建 RGBAHalf、linear=true、原 mipCount，整条数据 LoadRawTextureData，再 `Apply(false)`；不重生 mip。

本流程 SaveTexture 导出的 BC7_SRGB PNG 已经是 GPU 解码后的线性值，不能因原资源格式名再 sRGBDecode。线性 8 位 PNG 会损失暗部，所以最终静态材质改用 Half。ShaderLab Color 属性的源 CB 值也是 GPU 线性数，发布器在 SetColor 序列化边界编码 gamma 一次；Vector 不做此处理。详见 [颜色证据](../capture/texture-export-color-space.json)。

如果 EXR 已经归档，仅重跑 decode 即可，不用重新回放。`read_exr.py input.exr output.png` 只是会裁剪到 0…1 的预览，不用于 HDR 资产发布。

### 10.2 Cube11550

```powershell
$env:ENDFIELD_ROOT = $EndfieldRoot
$env:ENDFIELD_SOURCE_CAPTURE = "$EndfieldRoot/pro/Authoring/Work/SI1.rdc"
& $RenderDocExe --python "$EndfieldRoot/pro/Authoring/Tools/export_reflection_cube.py"
& $PythonExe -X utf8 pro/Authoring/Tools/decode_reflection_cube.py
& $PythonExe -X utf8 pro/Authoring/Tools/prepare_scene_import.py
```

当前 exporter 固定 SI1 的 event1122/RID11550；六面全部 8 mip 保存到 EnvironmentReflection/11550。总 blob 为 **源面 +X/-X/+Y/-Y/+Z/-Z → mip → 顶行 → float32 RGBA**，保留 HDR >1 和预滤波层。Unity 发布器集中处理换面/旋转，建立真正 Cubemap 和 Custom ReflectionProbe。

EnvironmentSH 的六个 3D 资源虽然已归档，本帧角色实际走 fallback 环境色分支，不能因为绑定存在就启用 SH volume。最终画面、GBuffer、逐 draw RT、源后处理 LUT 和历史颜色只作诊断，不是运行时背景或阴影贴图。

## 11. UI 生成的特殊顺序与覆盖范围

当前 UIPrepared 已经可供 Unity 发布。**仅在需要重生成 UI 时**运行：

```powershell
& $PythonExe -X utf8 pro/Authoring/Tools/prepare_ui_geometry.py
& $PythonExe -X utf8 pro/Authoring/Tools/build_ui_semantic_parameters.py
```

两步会写 `UIPrepared`，也会覆盖 **`pro/Assets/Endfield/Shaders/UI/*.shader`**。第一步建立几何/状态/临时 constants manifest 与程序包装；第二步将 CB 行转换为命名参数，生成 parameters 并移除 constants。

第二步不能在已经语义化的 manifest 上单独重复执行；重新生成应从第一步开始，并保留/核对现有手工维护的 Shader 改动。不要把这对脚本当成每次发布都必须运行的无副作用命令。

Unity 正式完整入口仍是 `PublishScene`。单独菜单 `Endfield/Authoring/Build SI1 UI Composition` 只对**当前相机**绑定并标记 scene dirty，不自动 SaveScene；单独调用后必须保存对应场景。

源 UI copy 只有 Y 翻转，UI 合成和最终 backbuffer 的方向适配必须分开。运行中 UI 先画内部 Composite RT，最后 Resolve 到目标时再适配 backbuffer。SceneView 不画 Game UI，Scene/Game 的后处理均有效。不能根据一张离屏相机截图随意再翻转角色或全部贴图。

## 12. 编辑器已打开时：文件命令桥

`EndfieldEditorBridge` 在 Unity update 中读取 `tmp/unity/commands/*.request.json`。它不使用 Computer Use，不发送键鼠。编译、导入或正忙时等待，按文件名排序执行。

可以在 PowerShell 定义一个投递函数；这是外部队列写入示例，不是新增工具：

```powershell
function Send-EndfieldCommand {
    param([hashtable]$Request)
    $queuePath = Join-Path $EndfieldRoot 'tmp/unity/commands'
    New-Item -ItemType Directory -Force -Path $queuePath | Out-Null
    $fileStem = (Get-Date -Format 'yyyyMMdd-HHmmss-fff') + '-' + $Request.id
    $pendingPath = Join-Path $queuePath ($fileStem + '.tmp')
    $requestPath = Join-Path $queuePath ($fileStem + '.request.json')
    $json = $Request | ConvertTo-Json -Depth 12
    [System.IO.File]::WriteAllText($pendingPath, $json, [System.Text.UTF8Encoding]::new($false))
    Move-Item -LiteralPath $pendingPath -Destination $requestPath
    Join-Path $queuePath ($fileStem + '.result.json')
}

$receipt = Send-EndfieldCommand @{
    id = 'publish-si1'
    action = 'invoke'
    argument = 'Endfield.Editor.EndfieldSceneBuilder.PublishScene'
}
# 等文件出现后读取回执；依赖此发布的下一条命令在完成后再发。
# Get-Content -LiteralPath $receipt
```

| action | argument / 行为 |
| --- | --- |
| `refresh` | AssetDatabase.Refresh；回执不表示后续编译一定成功，实际失败时读日志 |
| `invoke` | 完整 `Namespace.Type.Method`，公开 static 无参数方法 |
| `open-scene` | 如 `Assets/Endfield/Scenes/SI1.unity`，Single 打开 |
| `capture` | 相机取证，见第 13 节 |
| `quit` | 先回执再退出，不保存场景 |

处理时 request 改名为 running，结束另写 result。**正常完成也保留 `.running.json`**；以 result 的 success/detail 判断这次执行，不以 running 文件存在判断是否仍忙。失败后定位具体错误，不盲目重放可能已经写入资产的命令。

invoke 不能给有参数的方法传对象。因此 `EndfieldReflectionBuilder.Publish(GameObject,string)` 和 `EndfieldFrameCapture.Capture(Request)` 不直接用 invoke；前者由 SceneBuilder 调用，后者用 action:capture。

## 13. 截图与 RDC 验收：两条路径各自回答不同问题

### 13.1 Camera.Render 的固定机位截图与完整帧 RDC

需要 RDC 时，在启动有窗口 Editor 时加载 RenderDoc：

```powershell
& $UnityExe -projectPath $ProjectPath -accept-apiupdate -load-renderdoc `
  -executeMethod Endfield.Editor.EndfieldSceneBuilder.OpenScene `
  -logFile "$EndfieldRoot/tmp/unity/editor.log"
```

通过桥接捕获：

```powershell
Send-EndfieldCommand @{
    id = 'game-final'; action = 'capture'
    width = 2560; height = 1440; warmupFrames = 32; renderDoc = $true
}
```

默认主相机。SceneView 的当前视角可使用 `argument='scene-current'`；临时关后处理可设 `disablePostProcessing=$true`，阴影隔离可设 `disableShadows=$true`。除 scene-current 外，scene-* 会临时复制主相机姿态，不代表用户原来正在看的自由视角。

输出 `tmp/unity/captures/<UTC>/editor-camera.png`、`evidence.json`，RDC 请求成功时另有实际 capture 文件路径和 hash。Evidence 保存机位、矩阵、分辨率、GPU/API、相机类型与预热帧数。

当前工具先预热并 ReadPixels 同步，再 BeginCapture；正式 Camera.Render 后再次 ReadPixels，最后 EndCapture。此顺序解决了只截到 Bloom/后处理尾段的旧错误。进行帧对比时用实际成功的完整 capture；本机曾出现 SceneView 捕获驱动崩溃，现有问题与替代路径见 [editor-crash.md](../validation/editor-crash.md)。

这条工具临时设置非空 targetTexture，验证的是离屏相机渲染。它适合固定构图、GBuffer/光照/阴影对比，**不单独证明真实 GameView backbuffer 的 UI 方向正确**。

### 13.2 实际 GameView 的 UI 方向

有窗口 Editor 中先有已经渲染的 GameView，再调用：

```powershell
Send-EndfieldCommand @{
    id = 'real-game-view'; action = 'invoke'
    argument = 'Endfield.Editor.EndfieldGameViewCapture.CaptureCurrentGameView'
}
```

它持续 Repaint 约 2 秒后读取 `GameView.m_RenderTexture`，不替换相机 targetTexture，也不调用 Camera.Render。输出 `tmp/unity/game-view/<UTC>/game-view.png`、evidence.txt，最终路径记在 `tmp/unity/latest-game-view.txt`。

桥接 invoke 成功只说明异步入口返回，需等待实际 PNG 和最终路径记录。该工具依赖 Unity 6000.6 内部字段，不适合 `-batchmode -quit`。

PNG 保留内部 RT 的原始行序；D3D 下整张可能与 GUI 显示方向相反。判断 UI bug 时比较场景与 UI 的相对方向，并结合真实 Editor 截图。不要仅因 raw PNG 整体倒置，再把 UI 独立翻一次。本轮实际编辑器画面已由用户确认正确。

## 14. 多光源、局部修复与历史诊断入口

| 目的 | 入口与输出 |
| --- | --- |
| 普通多光示例 | `Endfield/示例/创建多光源场景` → MultiLightDemo.unity |
| 当前角色多光示例 | `Endfield/示例/创建角色多光源场景` → MultiLightCharacterDemo.unity，依赖已发布 SI1.prefab |
| 按灯隔离取证 | 当前 MultiLight 场景调用 `Endfield.Editor.EndfieldLightingStudy.CaptureLightingStudy`，只有 all case 捕 RDC，需已加载 RenderDoc |
| 更新源后处理预设 | `Endfield/Apply Source Post Process Profile`，会覆盖对应 Profile 参数 |
| 保留机位更新角色阴影 | `Endfield/Authoring/Publish character shadow settings` |
| 记录当前场景 | `Endfield.Editor.EndfieldVisualDiagnostics.RecordScene` → tmp/unity/scene-state.json |
| 归档被替代的发布资产 | `Endfield/Authoring/Archive superseded published assets` → Authoring/RetiredPublished |

多光示例用真实 Unity Directional/Point/Spot，示例预设与源 SI1 主灯/角色阴影 profile 各自独立。创建示例会重新写共享 Demo 材质/Profile，不用于改源角色材质参数。

以下历史工具不能误当常规流程：

- `CaptureOutlinePayloadOnly` 还引用已删除的 EndfieldOutlineColor Pass，已过时，不代表现在的描边隔离。
- `CaptureUrpDefaultsAtCurrentView` 名字未更新，实际读取 `tmp/unity/skin-shadow-camera.json` 的记录机位。
- `ApplyMaterialPasses` 会 SaveAssets，不是纯只读诊断。
- `verify_body_*` 依赖 SI1 的 538 原件和特定证据，不是所有角色的自动检查器。
- `EndfieldReflectionDiagnostics.Dump` 仍有旧工作目录/对象名假设，仅用于相应问题。

这些是已有工具的适用边界，并不要求每次重新生成都执行它们。

## 15. 清理与交付：只保留场景也能显示

保留完整 Unity 工程所需的：

```text
pro/Assets/Endfield/Runtime
pro/Assets/Endfield/Shaders
pro/Assets/Endfield/Content
pro/Assets/Endfield/Settings
pro/Assets/Endfield/Scenes
pro/Assets/Endfield/Editor       继续材质编辑时保留
pro/Packages
pro/ProjectSettings
以及所有对应 .meta
```

已经完整发布并保存后，`src`、`tool`、`tmp`、`pro/Authoring`、`pro/Assets/Authoring` 不属于运行依赖，可以单独归档或移除。可删除不等于可再生：删除 Authoring 输入/工具会失去重新提取、生成、取证菜单和来源研究能力。`Assets/Endfield/Editor` 的材质支持与 `Assets/Authoring/Editor` 的生成工具不是一个目录，不要一起误删。

PublicationCleanup 只按 Scenes/Prefabs/Settings 的显式依赖归档 Content 中未引用的 `.asset/.mat`，保存原 meta；它不是删除 Extracted 的工具，也不扫描任意字符串/Addressables 动态加载协议。当前工程采用显式资产引用，适合此归档方式。

资产边界详见 [asset-publication.md](../architecture/asset-publication.md)。

## 16. 换角色时哪些可以复用，哪些要重新建立

**复用机制，替换当前 capture 的证据映射。** 先找旧工程已经完成的结果，只补确实缺失或与新管线接口不同的部分。

| 可直接复用的基础 | 每份角色数据必须独立确定的内容 |
| --- | --- |
| Pipeline Asset / RenderPipeline / Renderer / Pass 职责 | 当前场景、相机和 Light 初值 |
| Unity 当前变换、剔除、光源/阴影/Probe 接口 | 源世界基底、character origin、posed/placed/baked 状态 |
| 已验证的同族 GBuffer/光照/前向/后处理公式 | 该角色实际启用的 keyword、CB 行、纹理通道和参数值 |
| Native/MCP 采集机制、world2 与纹理 blob 发布机制 | EID/RID、VS 输出 signature、CB bindSlot 与实例对应 |
| 原生材质/Prefab/场景发布与文件桥接 | 角色专用导入计划、UI 序列、FX/覆盖层、轮廓输入 |

建议按以下顺序移植：

1. 新建独立 `pro/Authoring/Extracted/<角色>`、内容目录和场景名，避免覆盖 SI1 资料。
2. 从旧工程的已完成导出与参数映射开始，先复用几何、静态纹理和同族公式。
3. 根据真实 Shader/绑定建立 GBuffer ↔ 受光事件对应；不要拿 SI1 的数值只换贴图。
4. 把当前硬编码 SI1 的生成入口提取为角色配置或为新角色增加明确的发布入口；不能只改 RDC 文件名。
5. 发布同样独立的 Unity 资产；动态相机、法线、灯光与阴影继续经过 Unity。
6. 在实际出现差异的部位做同机位截图/截帧对比，依据源值修复，而非目测随意调参。

本流程还原静态 pose 与当前 UI 绘制层，不恢复完整动画、交互逻辑或原游戏所有时序状态。当前 Unity TAA/空间 DOF/Bloom 与源 DOF/FSR 时域重建/Bloom 存在算法差异；已知视觉残差见 [进度](../progress/status.md)。

## 17. 从零重提仍未统一的步骤与历史脚本

以下缺口应在继续做通用工具时逐项收敛，不能因为已有结果存在，就写成“已具备一键复现”：

| 环节 | 当前已有内容 | 从空输入重提时还需要做什么 |
| --- | --- | --- |
| DCC 产物归档 | Source/world2、fbx、scene、stage | 将新 solve/emit 明确归档；当前 CLI 不自动写正式 Source |
| 源相机描述 | Source/capture-camera.json | 从新 read/parse 建 VP/frame；缺正式统一生成器 |
| 主 Source 证据归档 | Constants、Shaders、material-bindings 均齐备 | 修整 `tmp/capture/publish.py` 的会话与旧目的路径，或按第 6.2 节 schema 归档 |
| 553 首次补采 | CharacterSupplement/553 原 PostVS/IB；restore 正式入口 | 初采仍依赖历史 fix553-config/collect_config；restore 不造 FBX |
| 台面初次解算 | BackgroundRead、Background/world2、prepare 正式入口 | 缺 BackgroundRead 持久模板及一体 solve 入口 |
| 描边原件补采 | Outline/617/source-vb1.bin、TS2N 证据、world2 已含流 | outline635 模板目前无实际采集列表，需按真实 IA/资源补齐 |
| 阴影 HLSL | ShadowReceiverNative 实际 DXBC/CB/已归档 HLSL | native exporter 不反编译，尚无统一对应 HLSL 入口 |
| UI 重生成 | 两个正式生成脚本和已发布正确结果 | 生成器会覆盖 Shader，语义步骤非独立幂等，需要成对使用 |

历史脚本只用于理解当时的处理，不列入正常命令链：

| 位置 | 性质 |
| --- | --- |
| `tmp/capture/publish.py` | 首轮 Source 汇总器，输出路径陈旧 |
| `tmp/capture/fix553-config.py`、`complete553.py` | 首轮漏件补采/修复，依赖旧工作目录 |
| `tmp/capture/background-config*`、`background-solve*` | 初次背景补读和解算记录 |
| `tmp/capture/prepare-effects.py`、`prepare-ui.py`、`semantic-ui.py` | 正式 Tools 迁移前版本 |
| `tmp/capture/publish-authoring-tools.py`、`finish-tools.py`、`save-scripts.py` | 一次性迁移/保存脚本，不应重复用于当前发布 |
| `tool/rdc2dcc/SI1Scripts` 中旧 Python | 早期副本；当前持久版本优先用 Authoring/Tools |

因此，当前最短可靠使用路径是：**复用已经归档的 SI1 → 按需整理语义/导入计划 → PublishScene → 保存后的场景/Player**。需要从 RDC 重新补数据时，再进入对应的采集支路。

## 18. 参考资料与源码入口

- [项目总览](../../README.md)、[从场景到最终画面](rendering-walkthrough.md)。
- [外部工具来源与修改](../capture/tool-provenance.json)、[Authoring 工具归档记录](../capture/authoring-tools.json)；归档记录中的 hash 代表记录当时版本。
- [正式 Python 工具](../../pro/Authoring/Tools)、[Unity 发布工具](../../pro/Assets/Authoring/Editor)。
- [管线设计](../rendering/pipeline-design.md)、[着色模型和参数来源](../rendering/shading-models.md)。
- [坐标闭环](../capture/599-postvs-coordinate-check.json)、[N/T 修复](../validation/geometry-directions.md)。
- [描边证据](../capture/outline635-evidence.md)、[角色阴影源链](../capture/source-shadow-chain.md)。
- [UI 参数映射](../capture/ui-parameter-mapping.json)、[真实 GameView 方向修复](../validation/ui-game-view-orientation.md)。
- [多光源示例](../rendering/multi-light-demo.md)、[当前验收与剩余边界](../progress/status.md)。
