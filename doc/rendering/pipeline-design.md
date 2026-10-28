# 渲染管线

运行版本为 Unity 6000.6.3f1，依赖 SRP Core 17.6.0。主工程根是 `pro/`。旧工程只用于读取既有 GBuffer 契约和已研究的材料表达式；新的运行管线不读取 RenderDoc 事件号、常量缓冲页或截帧资源图。

## 从哪里开始读

1. `EndfieldRenderPipelineAsset`：创建管线资产，配置比例、阴影、光源上限和全屏 Shader 引用。
2. `EndfieldRenderPipeline`：按 Camera.depth 排序，对每个相机调用 Unity 剔除，更新该相机独立的 VolumeStack，提交命令。
3. `EndfieldScriptableRenderer`：准备当前相机资源，设置实时相机矩阵，按固定顺序执行小型 Pass。
4. `Passes/`：Shadow → Outline → GBuffer → Lighting → Transparent → PostProcess → UI。

运行代码统一在 `pro/Assets/Endfield/Runtime/Rendering/`，命名空间为 `Endfield.Rendering`。没有自定义复杂图执行器，也没有按角色名选择光照算法的分支。

Asset还提供Unity标准defaultShader/defaultMaterial入口，普通新建3D对象可直接使用通用HybridLit。相机循环同时支持Game、SceneView和Preview，不为材质预览另写一套光照；UI仅在Game绘制。每相机的VolumeStack、实时参数和临时目标相互隔离。

## Pass 的职责

| Pass | 输入 | 输出/职责 |
|---|---|---|
| Shadow | 当前相机剔除、Unity可见主方向光 | Unity实时级联阴影图和世界到阴影矩阵 |
| Outline | 普通Renderer、EndfieldOutline材料Pass | 向与主体相同的五个MRT和深度写出描边 |
| GBuffer | 普通Renderer、EndfieldGBuffer材料Pass | 主体材料五个MRT和深度 |
| Lighting | 五个MRT、深度、动态光源和阴影 | 全屏延迟光照，然后用EndfieldSurfaceLighting重绘有独立源受光公式的可见表面 |
| Transparent | HDR场景颜色、已写深度 | 按CommonTransparent排序的EndfieldForward材料；按相机设置绘制Skybox |
| PostProcess | HDR颜色、相机VolumeStack | 曝光、Bloom、色调映射、对比度、饱和度、暗角或GBuffer调试图 |
| UI | 最终相机目标 | Unity原生UIOverlay；编辑器Gizmo |

`RenderPipeline` Shader 标签为 `EndfieldPipeline`。阴影使用标准 `ShadowCaster` LightMode。透明队列目前需要显式提供 `EndfieldForward` Pass；普通 Built-in/URP 材质不会自动改写成这套 GBuffer。

## GBuffer 契约

以下为旧工程实际五MRT接口在重构管线中的保留。表中材料语义是通用PBR分支；源角色分支保留自己的原始payload，不能把某个旧材质族推测扩展成所有角色的固定游戏语义。

| 附件 | GraphicsFormat | 重构后的约定 |
|---|---|---|
| `_GBuffer0` | B10G11R11_UFloatPack32 | 材料自发光/附加辐射颜色 |
| `_GBuffer1` | A2B10G10R10_UNormPack32 | xy保留四次根motion编码（静止0.5）；zw保留材料标量与响应 |
| `_GBuffer2` | A2B10G10R10_UNormPack32 | xyz为metallic/occlusion/specular数据；w为两位材料族数据 |
| `_GBuffer3` | A2B10G10R10_UNormPack32 | xy为Y-up八面体法线；z为roughness；w为两位材料族数据 |
| `_GBuffer4` | R8G8B8A8_SRGB | rgb为baseColor（RT自动sRGB转换）；a为材料族payload |
| `_CameraDepthTexture` | D32_SFloat_S8_UInt | 当前相机设备深度；平台不支持时改D24_UNorm_S8_UInt |

颜色附件不受支持时使用 RGBA16F。所有附件均为当前相机像素尺寸乘renderScale，MSAA为1。运动通道保留接口，但当前没有TAA或上一帧骨骼/物体矩阵；静止编码不等于已完成动态motion实现。

SI-1源角色的 `_GBuffer2` 是实例10/10/10/2 payload，`_GBuffer3.z=0`，不能按通用metallic/roughness解码。Lighting阶段为材料提供 `EndfieldSurfaceLighting` 几何Pass入口：先计算全屏延迟背景/普通材质，再在同一HDR颜色和深度上用ZTest Equal恢复角色自己的表面受光。该能力由材料Pass选择，不在C#内按角色名、资源ID或事件号分支。

`EndfieldDebugView`：Final、Emission、Motion、Material、Normal、Roughness、BaseColor、Depth、Shadow。可由资产设置，也可由 `EndfieldCameraSettings.overrideDebugView` 为某个相机覆写。

## 实时参数

相机每次绘制重新计算 `GL.GetGPUProjectionMatrix(camera.projectionMatrix, true)` 和逆VP。网格变换由Unity的逐物体矩阵传入，法线由材质Shader做逆转置变换。不会恢复旧的固定Camera或Light缓冲。

主光优先选当前剔除结果中的 `RenderSettings.sun`，否则选最亮的可见方向光。通过Unity `ComputeDirectionalShadowMatricesAndCullingPrimitives` 得到1、2或4级联矩阵和caster剔除球，`CreateShadowRendererList` 绘制真实caster。每个级联在单张图集中占一个tile，Z反转和atlas变换遵循SRP的ShadowUtils方法。灯光自身的shadowBias、shadowNormalBias、shadowStrength和shadowNearPlane参与计算。

阴影投射资格由Unity `Renderer.shadowCastingMode`控制，不能因为材料是opaque就把它默认当caster。实际故障中，SI-1背景壳1190与环境655被误设On，在图集中覆盖大片近端depth=1，使整个角色处于阴影。只排除这两类后，实际Raw atlas出现角色轮廓，PCF恢复正常受光/自阴影；证据为 `tmp/unity/shadow-character-isolation.json`。已对应主体caster为488/520/538/553/568/585/599/617，眼502、环境655、壳1190没有对应源shadow draw；后续补充确认Shadow424对应部件1649，在其表面尚未迁完时用Unity标准ShadowsOnly保留真实遮蔽件。该源资格由Authoring初始化真实Renderer组件，C# Pass本身不维护事件号列表。

设备深度也不能凭截图倒置猜测修复。此Unity版本命令clear的逻辑depth=1会转换为reverse-Z设备0；实际将逻辑clear改0使Raw图整张成为1，已据此恢复正确逻辑1。最终没有添加生产shadow Yflip。场景CSM及附加灯的caster偏移使用Unity标准负depth/normal bias，normal偏移为向内收缩。

硬/软阴影由Unity Light.shadows选择。Hard使用一次原生比较；Soft直接调用Core `ShadowSamplingTent.hlsl` 的5×5 Tent采样位置/权重（9次双线性比较），并按相同Unity核半径2.5缩放caster bias。生产调试菜单只保留常用GBuffer、Depth、Shadow和RawShadow，不保留本次定位中的手动深度比较或Yflip实验选项。

角色另有独立局部阴影路径。新侧胸机位暴露了仅用CSM替代源角色可见性的缺口；补取914/372后，Shadow阶段新增`EndfieldCharacterShadowPass`，按实时主Light与显式caster包围盒构建D16投影。该路径使用position-only caster、源3/6纹素的片元接收偏移和16 Gather过滤，角色索引由组件经Unity PropertyBlock传递。它与普通CSM共享阶段但不混用接收公式、深度格式或偏置。完整设计与参数出处见[角色局部阴影](character-shadows.md)。

环境使用真正的Unity `RenderSettings.ambientProbe`。几何Renderer由 `PerObjectData.LightProbe`读取Unity标准SH9；全屏阶段由 `SHCoefficients(RenderSettings.ambientProbe)`打包同一组七个向量，避免把Custom环境误当天空/地面渐变。`EndfieldEnvironmentLighting`保存场景的可编辑线性常量环境辐照度，在OnEnable/OnValidate恢复Custom SH L0；因为Unity不会把运行时ambientProbe系数直接序列化进场景，不能只在一次性builder中赋值。移除组件时恢复此前的Unity环境。

额外方向光、点光、聚光直接来自Unity `CullingResults.visibleLights`，最多32个，主方向光不会重复计入。CPU传递位置、颜色、逆距离平方、聚光方向以及inner/outer angle。位置、旋转、范围、颜色、强度及色温可在Unity中编辑并立即生效。管线按Unity约定启用线性灯强与色温，并在释放时恢复此前GraphicsSettings。当前不是clustered/forward+；大量灯光时每像素线性遍历会增加成本。

共享Shader接口：

| 参数 | 数据 |
|---|---|
| `_MainLightDirection`, `_MainLightColor` | toward-light方向、线性颜色 |
| `_AdditionalLightCount` | 当前相机局部光数量 |
| `_AdditionalLightPositions[32]` | w=0时xyz为toward-light方向；w>0时xyz位置、w逆范围平方 |
| `_AdditionalLightColors[32]` | 线性颜色 |
| `_AdditionalLightSpotDirections[32]` | xyz灯光朝外的方向 |
| `_AdditionalLightSpotAngles[32]` | xy角度scale/offset；点光为(0,1) |
| `_MainLightWorldToShadow[4]` | 含atlas变换的世界到阴影矩阵 |
| `_MainLightShadowCascadeSpheres[4]` | xyz世界空间球心，w半径平方 |
| `_MainLightShadowParams` | strength、级联数量、1/atlasSize、最大距离 |
| `_ShadowBias`, `_ShadowLightDirection` | caster世界空间偏移参数、toward-light方向 |
| `_EndfieldInverseViewProjection` | 当前相机逆GPU VP |
| `_EndfieldScreenSize` | width、height、1/width、1/height |

## 资源、Volume和最终方向

当前使用清晰的临时RenderTexture生命周期，不引入持久历史图。`EndfieldCameraTargets.Allocate` 为当前相机申请基础目标，启用的效果再申请其专属目标，当前相机所有Pass共享，在Renderer的finally中统一释放。相机按顺序提交；后一个相机重新设置所有矩阵、灯光、阴影和Volume参数，不沿用前一相机的帧状态。唯一跨帧状态是每相机独立VolumeStack，其相机销毁时释放。

实际深度附件的内部资源名为 `_EndfieldCameraDepthAttachment`；Shader采样接口仍为 `_CameraDepthTexture`。只有源Scene确实存在soft-intersection消费者1554/1672/1693/1730时，Authoring启用 `requireOpaqueDepthTexture`：在opaque阶段结束、透明开始前，先解除DSV绑定，再对整张同格式深度执行Unity CopyTexture到独立 `_EndfieldOpaqueDepthTexture`，并把采样全局切到该副本。透明几何深度测试仍绑定原附件，避免D3D11把同一资源同时当DSV和SRV造成反馈。四件源淡出公式为 saturate((sceneViewDepth-particleViewDepth+offset)/distance)，distance分别为.001/.001/.1/.001；不加载捕获Depth，也不对没有此消费者的场景增加拷贝。副本同样属于当前相机生命周期。

后处理遵循Core标准 `Volume` / `VolumeProfile` 工作流。基础显示用 `Endfield/Post Process`，源功能分别为 `Depth Of Field`、`Source Bloom`、`Source Display`、`Color Grading LUT`。`EndfieldCameraSettings` 配置volumeLayerMask和volumeTrigger，支持标准全局/局部Volume混合。SceneView与Game相机使用相同后处理路径；仅Game调用UI。

全屏绘制通过三角形SV_VertexID和显式 `_SourceTexture`、`_SourceScaleBias`。`SetViewProjectionMatrices`接收CPU相机投影，由Unity转换；`GL.GetGPUProjectionMatrix`只参与自定义逆VP，避免二次投影转换造成倒置。最终后处理先写独立的线性显示颜色 `_EndfieldUIResolvedSceneTexture`，再落相机目标。UI合成以该实时结果为初始场景，既不采样最终目标造成反馈，也不重新经过曝光/Bloom。相机RenderTexture与backbuffer的最终方向通过显式scale/bias处理。

## SI-1后处理源值与语义映射

源证据在 `doc/capture/post/` 的反汇编和 `*_cb*.json`。原始导出/工具资料位于可单独移除的 `pro/Authoring/Extracted/SI1/Source/`；Runtime不读取这些文件。`Assets/Authoring/Editor/EndfieldPostProcessBuilder.ApplySourceProfile` 一次性将以下已定位值写成Volume资产，删除Authoring后仍可运行。

| SI-1源字段 | 语义 | Volume/运行时映射 |
|---|---|---|
| CS1742 cb1[1].xyz=(0,0,0) | 近景CoC区间和幅度关闭 | DOF.nearStart/nearEnd/nearRadius |
| CS1742 cb1[2].xyz=(9,20,1.4099999666) | 远景CoC从9到20，模糊幅度1.41 | DOF.farStart/farEnd/farRadius |
| CS1742 cb0[2].zw | 设备深度到线性距离 | 不保留源相机数字；Shader使用当前Unity相机深度参数 |
| CS1960 cb1[1]=(.522521615,.261250794,.522541642,.956861556) | Bloom软阈值 | thresholdGamma=.75, softKnee=.5；CPU先GammaToLinear，再knee=threshold*.5+1e-5，生成(threshold,threshold-knee,2*knee,.25/knee) |
| CS2041至2104 cb0[0].x=.7699999809 | Bloom逐层上采样混合 | Bloom.scatter；不是整体强度 |
| CS1960至2032输出尺寸1280x720→5x3 | 9层Bloom金字塔 | Bloom.maxIterations=9；各RT尺寸随当前相机实时计算 |
| PS2148 cb1[9].x=.3660402298 | 场景/Bloom合成权重 | Bloom.intensity |
| PS2148 cb1[9].z=0 | 场景高光抑制比例 | SourceDisplay.bloomHighlightSuppression |
| PS2148 cb1[11].xyz≈(1,1,1) | Bloom颜色乘数 | Bloom.tint，按源浮点值写入预设 |
| PS2148 cb0[27].x=1 | 场景曝光乘数 | PostProcess.exposure=0EV，不沿用固定CB |
| PS2148 cb1[7]=(1/1024,1/32,31,1) | LUT strip尺寸/格点/后曝光 | 由实时生成的32³ strip计算，当前postExposure=1 |
| PS2148 cb1[1].xy=(.5,.5), w=0 | 暗角中心与纵横混合控制 | SourceDisplay.vignetteCenter/vignetteAspectBlend |
| PS2148 cb1[2]=(.900000036,2.049999952,1.299999952,0) | 暗角横向形状、边缘幂次与纵横补偿 | SourceDisplay.roundness/falloff/exponent/aspectCompensation；这是按公式职责命名，不声称恢复了游戏UI字段名 |
| PS2148 cb1[4].xyz=(.0666666701,.0671745762,.0745098069) | 暗角颜色 | SourceDisplay.vignetteColor，按原公式值传递，不二次转换颜色 |
| CS2114/2123/2132 的2.5 | 每样本高亮限幅阈值 | 不是blur radius；Shader保留SourceUIBlur功能，但本帧95个UI draw无动态blur输入，管线不分配无消费者RT |

DOF CoC公式保留源的近/远分段：near=-saturate((depth-nearEnd)/(nearStart-nearEnd))，far=saturate((depth-farStart)/(farEnd-farStart))，far>0时取far；区间相等或该端radius=0时关闭。当前DOF使用单帧13tap空间核，尚未恢复源11阶段的分层散景和CoC/颜色历史，这是明确差异，不能称逐像素等价。

Bloom预过滤采用源13tap抗闪烁/亮度加权核；降采样采用源binomial9×9的25tap双线性重组，上采样使用和源相同的bicubic公式。没有用简单高斯两次模糊冒称源Bloom。源共享内存中的半浮点量化细节仍有差异。基础PostProcess的简化Bloom保留为可编辑基线，但源预设将其强度设0，避免同时叠两份。

金字塔尺寸直接按完整画面除以2的各级幂后取近整数，符合源高度720→360→180→90→45→23→11→6→3。不能反复把上一层整数除2，否则奇数高度会累积偏小。当前相机尺寸改变时仍用相同规则重新分配。

源显示先合成曝光/高光抑制/Bloom/暗角，再执行精确的源LogC编码和32³ LUT采样。LUT不是线性颜色直接saturate采样。最终保留线性显示RGB，让Unity目标执行显示sRGB编码；源UI的displayRGB混合由独立UI renderer处理。

### LUT producer的18行语义

旧已验证 `ColorLookupTable.hlsl` 的数学现移植为 `SourceColorLut.hlsl`，去掉外部原始CB接口。`EndfieldColorLutBuilder` 每相机用Volume语义生成1024x32 RGBAHalf目标，八张输入是ShaderRead曲线或数学中性曲线，不是捕获LUT结果。

| 旧producer行 | 新语义字段 |
|---|---|
| 0/1 | 原算法未消费，省去 |
| 2 | LUT尺寸、half-texel和32/31格点比例（实时计算） |
| 3 | temperature/tint → ColorUtils.ColorBalanceToLMSCoeffs |
| 4 | colorFilter.linear |
| 5/6/7 | channelMixerRed/Green/Blue |
| 8 | hueShift/360、saturation、contrast |
| 9/10/11 | lift/gamma/gain → ColorUtils.PrepareLiftGammaGain |
| 12/13/14 | shadows/midtones/highlights → ColorUtils.PrepareShadowsMidtonesHighlights |
| 15 | tonalRanges：shadowStart/end、highlightStart/end |
| 16/17 | splitShadows/highlights/balance → ColorUtils.PrepareSplitToning |
| 曲线0/1/2/3 | master/red/green/blue |
| 曲线4/5/6/7 | hueVsHue/hueVsSat/satVsSat/lumVsSat |

SI-1没有定位到LUT producer CB。旧工程的saturation=1.08、shadow multiplier=.894736886是原producer GPU输出验证下的非唯一推定值，不能叫直接捕获CB值。随后对SI-1真实LUT（SHA256 b64157ec4524027fc768d10001e0994da630de8fd20c4dbe7d91263b7f4de1d3）和旧成熟参考LUT（20988edbd274f7ef4bd72dcdb4097f8ca571532aa5740c1f271a91728e3fa4b4）逐half比较：130679/131072组件相同（99.700%），MAE=5.9518e-7，最大差.00146484375。这支持两帧采用同一成熟映射，因此源预设现启用该语义重生成：saturation=1.08，shadows=(1,1,1,-.1052631139755249)，通过Unity ColorUtils得到线性shadow multiplier=.894736886。仍保留“非唯一推断”标记；不通过曝光或灯光补偿颜色。

四张原始RGB/master曲线实际为128点 `i/128`，末点.9921875；四张HSV曲线恒.5。producer自身加half-texel，因此数学中性曲线也必须使用 `i/128`，不能改成 `i/127`。运行时直接生成这些数学曲线，无需把任何捕获LUT结果作为输入。真实SI-1 LUT raw仅用于tmp离线对比。

实际Unity新producer重生成结果已直接与SI-1比较：130681/131072个half组件相同（99.7017%），组件MAE=5.93304e-7，最大差.00146484375；不翻行的原生顺序匹配，反转行后MAE升为.289。统计及完整哈希见 `source-lut-regeneration.json`。该结果来自新语义接口、当前Unity GPU执行和数学曲线，不是复制参考像素。剩余差异原因尚未确定，不能称完全bit exact。

### 背景亮度的实际颜色空间问题

1190背景两侧的源不透明HDR在1506×846位置(60,423)/(1440,423)为(.6640625,.6640625,.65625)。Unity无后处理截图同处PNG为(169,169,169)，反解sRGB得到(.396755,.396755,.396755)。差异已经发生在后处理之前，不能用曝光、LUT或灯光补偿。

实际Unity RenderDoc draw843中，`_EffectColor`由源线性值.8214345变为.640797615。这正是ShaderLab Color属性的自动sRGB解码；源参数发布时应把线性色转换为Inspector颜色，再由Unity上传恢复线性值。该转换属于离线材质发布边界，运行时shader继续使用正常线性颜色。

背景24403原SRV确为BC7_SRGB，但RenderDoc SaveTexture的PNG已经是解码后的线性像素。真实PickPixel/EXR在(0,0)为.9296875，PNG为237/255；(32,32)为(.9140625,.90625,.9140625)，PNG为(233,231,233)/255。新旧PNG逐字节一致。于是该PNG应发布为线性Texture，不能再次根据原SRV的SRGB后缀做解码。1190的绑定已单独改为`srgb=false`；这不是对所有PNG做同样假设。原证据仅用于离线诊断，路径为`tmp/capture/texture-color-probe`。

实际修正后，Unity Scene无后处理截图`tmp/unity/captures/20261026-200815-644/editor-camera.png`两侧(60/1440,423)为213/255，反解HDR=.665387，对源R11=.6640625；顶部(60/1440,60)为187/255，反解HDR=.496933，对源翻行对应=.496094。残差处于PNG量化与源R11精度范围，背景亮度问题已在后处理前定位并修复，没有修改效果公式、曝光、灯光或LUT来补偿。

源`final-with-ui.png`还有大量非255的alpha，直接嵌图会引入查看器的背景合成。后续应比较RGB和GPU原始RT，并按源最终UI的Y方向转换，不能单凭透明PNG的肉眼明暗调整渲染参数。

### Unity反射探针接口

表面受光读取Unity自动选择的`unity_SpecCube0`及标准HDR解码、包围盒参数，运行时不按来源事件或贴图ID选择环境。RendererList沿Unity Forward方法同时请求`PerObjectData.ReflectionProbes | PerObjectData.LightData`。全局环境由`RenderSettings`和标准ReflectionProbe组件配置；Custom Cubemap仅在离线资产发布时建立。

编辑器诊断曾显示ReflectionProbe.texture、customBakedTexture、defaultTexture均为有效的同一Cubemap，599 Renderer的GetClosestReflectionProbes选择Environment、weight=1，Camera剔除也含NeedsReflectionProbes。后续GPU检验必须先确认材质实际编译了反射关键字；只有四张2D贴图的shader变体根本未执行cube采样，不能以其槽位判断native probe绑定失败。

最终真实Unity帧086的599 draw960已经确认t7声明为texturecube并执行sample_l，Resource13048为EnvironmentReflection，128²、8mip、RGBAHalf。证据见`doc/validation/reflection-binding.json`。没有运行时来源Cube手动绑定；该路径由Unity组件、RendererList标准逐物体数据和正确材质关键字驱动。

### 材质Pass选择

`Endfield.Editor.EndfieldMaterialSetup.Apply(Material)`由材质Inspector与离线发布共用。普通不透明表面只启用GBuffer；源角色增加SurfaceLighting；源效果只启用Effect；透明材质使用Forward或Effect；通用Outline由世界宽度选择，源SurfaceOutline由独立功能和屏幕宽度选择，二者互斥。GBuffer阶段按queue≤2499表面→SurfaceOutline只写RT0→queue2500远景几何排序，面部/眼睛保护用已确认的Stencil bit16。RendererList按LightMode统一调度，无来源事件分支；同一透明RendererList接受Forward/Effect两个候选。ShadowCaster由Renderer.shadowCastingMode控制。

### 时序抗锯齿与运动输入

SI-1原后处理包含时域升采样，不是单纯的原生分辨率TAA：1871解码motion，1887生成速度和深度数据，1932读取历史/速度/lock，1941读取当前HDR21332、历史20321、速度20523、曝光20325、lock20527并输出20305/20539/20531，1950继续重建/锐化。1941 CB尺寸为render1506×846、display2560×1440，row4当前jitter=(.34375,-.240740776)、previous=(.28125,-.092592597)。旧成熟工程也有颜色/权重、亮度、lock等FSR历史，不能把它称作普通TAA直接搬进新工程。

新管线先提供本机Unity URP TemporalAA High的通用原生分辨率方法：3×3 YCoCg方差和min/max约束、最近深度运动扩张、五次双线性Catmull-Rom历史采样、感知亮度加权。默认当前帧权重.1、方差尺度.9来自Unity默认设置。它在PostProcess入口、DOF/Bloom/显示映射之前处理线性HDR，没有导入捕获最终结果，也不声称等价于源FSR的升采样、lock与锐化。

阶段顺序也有明确差异：源1742～1834先执行DOF，1871～1950再时域升采样，然后1960+ Bloom；当前公共实现采用Unity TAA→单帧空间DOF→Bloom。没有用新TAA冒称源DOF历史或原FSR重建。

每Camera拥有独立RGBAHalf颜色历史和Halton(2,3)序号，按实际渲染次数推进，而非Time.frameCount；同一个Editor update内连续Camera.Render16次仍会取得不同子像素样本。分辨率或投影变化、关闭AA、切换调试视图会重置。普通相机移动由非jittered当前/前帧矩阵重投影，显式切镜可调用EndfieldCameraSettings.ResetTemporalHistory()。静止SceneView会有限地追加绘制至16次积累；离屏截图建议预热16～32次。

运动是独立RGHalf纹理，不从GBuffer1的压缩payload推导：先用当前深度和Unity矩阵生成camera motion，再用EndfieldMotionVectors Pass覆盖可见不透明网格。该Pass按Unity ObjectMotionVectors约定使用unity_MatrixPreviousM；蒙皮前帧顶点读取TEXCOORD4，unity_MotionVectorsParams.x/y遵循Unity的旧顶点与ForceNoMotion控制。RendererList请求MotionVectors，Camera同时请求Depth|MotionVectors。jitter只用于光栅矩阵，motion使用非jittered矩阵，避免抵消应被积累的子像素覆盖。Camera.projectionMatrix属性不被改写，用户自动透视/正交和动态镜头仍由Unity管理。

通用HybridLit支持对象与蒙皮运动；其他自定义shader可提供同一LightMode接入。未提供motion pass的shader使用camera motion；透明粒子的独立运动/反应遮罩暂未恢复。源FSR时域升采样、lock历史和完整遮挡重建仍是与本轮原生分辨率TAA的明确差异。

## 明确的当前范围

- 实现实时主方向光级联阴影，以及额外方向光单张、点光六面、聚光单张阴影；烘焙ShadowMask尚未接入。独立多光源示例与实际验收入口见`multi-light-demo.md`。
- 原生分辨率TAA与Unity动态相机/对象motion已接入；源FSR时域升采样、屏幕空间反射、AO和完整时序后处理尚未恢复。DOF、Bloom、LUT、源显示接口已恢复，其中DOF分层/历史和LUT源grading值差异如上。
- 没有相机叠加合成；每个相机独立完整绘制。`CameraClearFlags.Depth/Nothing` 不代表复用上一相机的临时MRT。
- 保留GBuffer布局不代表已证明所有SI-1材料族公式。角色材质应通过实际截帧证据逐项恢复。
- 需以最终Unity编译、编辑器截图和RenderDoc帧验证图像方向及阴影。本文不会把代码完成当作画面对齐结论。

实现时参考本机Unity6000.6.3f1内置Core的 `Runtime/Volume/VolumeManager.cs` 与URP的 `Runtime/ShadowUtils.cs`、`Runtime/Passes/MainLightShadowCasterPass.cs`。这些仅为Unity动态资源/矩阵方法的参考；新工程不依赖URP运行时。
