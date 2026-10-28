# 材质模型、源公式与 Unity 接口

本工程把材质参数公开为用途明确的名称。源常量页只由离线导入脚本读取，数值固化到普通 Unity Material；运行 Shader 不声明捕获 CB 页，不以 EID、ResourceId 或程序哈希分派算法。程序对应证据在 `doc/capture/shaders`，后处理对应证据在 `doc/capture/post`。

`Endfield/HybridLit` 通过 local keyword 选择 Face、Eye、Cloth、Hair，并组合源法线、覆盖率、视角染色、源环境和特效功能。新创作的通用 PBR 材质与已有源材质共用变换、法线编码、光源、阴影和写出接口；不得把新创作 `_MaskMap` 的约定直接套到源 ILM。

## 帧接口

| LightMode / Shader | 职责 |
| --- | --- |
| `EndfieldGBuffer` | 五附件与当前场景深度；源角色/源环境按自己的字段布局写出 |
| `Hidden/Endfield/DeferredLighting` | 当前深度重建世界坐标，处理环境/普通 PBR 表面 |
| `EndfieldSurfaceLighting` | 源角色在相同几何深度处读取自身材质，计算专有受光 |
| `EndfieldEffect` | 源不透明前向效果；实际混合/深度状态来自材质 |
| `EndfieldForward` | 独立透明前向阶段 |
| `ShadowCaster` | 当前几何、Camera/Light 矩阵与 Unity 偏移参数生成实时阴影 |
| `CharacterShadowCaster` | 当前角色组的实时Light/bounds投影；位置路径、CullOff、D16、源raster偏移，不执行顶点normal bias |
| `EndfieldOutline` | 可选的通用世界单位挤出轮廓，写完整GBuffer |
| `EndfieldSurfaceOutline` | 源屏幕轮廓：前景GBuffer之后、远景GBuffer之前，只写RT0与深度；不另向SceneColor硬写黑色 |

方向、点、聚光由 Unity Light 提供。主光 cascades、图集、深度/normal bias 由 C# 当前相机建立。角色间接光读取 Unity 每物体 LightProbe/ambientProbe 的 SH9。

SI-1 本帧的实际环境分支已经确认：1040 PS 第71条及其它角色对应位置检查 `G[111].y < 0.5`，捕获值为1，因此 3D SH 路径不执行，else 直接使用 `G[112].rgb=(0.8490771055,0.8957685828,1.1509230137)`。场景以该真实值初始化 Unity Custom ambientProbe 的 L0：各通道系数直接等于线性颜色，其它阶为零。Core `Runtime/Utilities/BatchRendererGroupGlobals.cs` 的 `SHCoefficients.GetSHA` 直接把 `sh[c,0]-sh[c,6]` 放入 Shader 常量，Unity 存储已预缩放，不能再除标准数学 SH 基底的0.282095。数值不再进行 gamma 转换，也不在材质里硬塞源页。本机 Unity 6000.6.3f1 的 AmbientMode.Custom 枚举值已确认是4。六个实际绑定但本帧不活跃的3D volume保存在离线 EnvironmentSH，不能擅自用它们替换本帧生效的 fallback。

## 五附件契约

| 附件 | 格式 | 源角色 | 源环境 |
| --- | --- | --- | --- |
| 0 | B10G11R11 UFloat | 源普通角色为零 | 源 655 为零；alpha 0.5 不存在于该实际格式 |
| 1 | A2B10G10R10 UNorm | XY 带符号四次根运动，Z=1，W=0.4 | XY 运动/禁用中性，Z 材质光照字段，W 禁用标记 |
| 2 | A2B10G10R10 UNorm | 实例字段按 10/10/10/2 位解码；不是金属度 | 金属、遮蔽、源镜面参数、标签高两位 |
| 3 | A2B10G10R10 UNorm | XY 为 Y-up 八面体法线，Z=0，W 家族标签 | XY 同编码，Z 粗糙度，W 标签低两位 |
| 4 | RGBA8 sRGB | 线性基础色经 sRGB 附件存储，A=1 | 基础色，A=0 |
| 深度 | D32 Float / S8 | 当前几何 | 当前几何 |

0.4 等 alpha 输入由真实 A2 格式量化为 1/3，不能以 RgbaHalf 输出比较认为通道不一致。法线的折叠轴是世界 Y，不能替换成通常以 Z 为主轴的 oct 编码。静止运动编码为 0.5。当前运动输入覆盖相机运动；完整对象/蒙皮前帧流尚未接入。

## SI-1 的程序对应

| GBuffer draw / hash 前缀 | 功能 | 表面受光 draw |
| --- | --- | --- |
| 488 / 479a1a25 | 几何法线、基础色（FaceDetail，仅面部细节小网格） | 1040 |
| 502 / 479a1a25 | 几何法线、基础色（Eye） | 1061 |
| 520 / b3ed3da6 | RG/A 法线解码、基础色 | 997 |
| 538 / f3ad6268 | 身体皮肤/纹身，法线与视角染色 | 1019 |
| 553、568 / f3ad6268 | 眼周面部细节/完整面部皮肤，共享专有模型 | 1082、1101 |
| 585、599 / b3ed3da6 | 法线、基础色 | 1122、1143 |
| 617 / d2a926b5 | 覆盖率裁剪、RG 法线（Hair） | 1165 |
| 655 / 08ed673f | 环境多 UV/PBR 遮罩 | fullscreen deferred |
| 1190 / 977aae30 | 不透明前向特效 | 自身 |
| 1649 / 独立 LayeredCloth | 前向专有分层衣料，无普通GBuffer绘制 | 自身，处于late FX几何顺序 |

GBuffer 的 b3ed3da6/f3ad6268 在旧 lino1/typhon2 的原反汇编中有对应，不需重做旧算法证明。上述源公式已切成语义函数，源的法线 Z 在 XY 乘强度前重建、背面行为、视角染色 0.85/0.15、覆盖率 discard 和实例位字段均保留。Hair/Face/Eye 的语义分类同时依据本次实际基础色贴图，并未根据旧角色名字套用。

实际逐draw颜色证据明确：1625结束时衣料仍为基础深蓝圆纹，1649完成后立即出现最终白色菱纹。它不是应该在585的基础色里绘造的图案。1649本身使用相同95727/96071/95383基础色/遮罩/法线，但属于单独几何覆盖层，M[2].x=1输出纹理Alpha、M[1].z=1，RGB不额外预乘，One/OneMinusSrcAlpha并且ZWrite开启。其实际postVS normal/tangent已独立保存在Effects1649，不能使用粒子默认法线；surface UV与原随机阴影424的UV逐bit相同。

## 材质参数映射

以下 `M` 指各源程序的材质 CB：普通 GBuffer 为 PS slot2，视角染色为 PS slot3；Forward 为 PS slot6。`G` 指 Forward PS slot1 的场景风格配置。置信度“高”表示可直接从采样/算术操作确定；“中”表示用途由上下文推断，完整周边组合尚需继续适配。

| 对外字段 | 源位置 | 用途 / 置信度 |
| --- | --- | --- |
| `_BaseColor` | M[6].rgba | 纹理乘色，高 |
| `_NormalScale` | M[0].w | 切线 XY 强度，高 |
| `_BackFaceNormal` | M[1].y | 源角色背面法线混合，高 |
| `_SourceMipBias` | GBuffer frame[26].x | 采样 mip 偏移，高 |
| `_BaseMap_ST` | GBuffer VS material[10] | 当前 UV 缩放偏移，高 |
| `_SourceInstancePayload` | instance[5].z 的 uint 位模式 | 10/10/10/2 位字段，高；字段进一步业务名称待定 |
| `_ViewTintStrength`、`_ViewTintColor` | M[12].x、M[13].rgb | 视角染色，高 |
| `_Cutoff` | 617 M[12].x | 覆盖率 R 裁剪，高 |
| `_Roughness` | 1 - Forward M[0].x | 普通表面粗糙度，高 |
| `_Specular`、`_Metallic` | Forward M[0].y、z | 介质 F0 缩放 / 金属权重，高 |
| `_SourceMaskMap` | 997 t17；1122/1143 t18 | R金属、G高光、B细节、A光滑，高；与通用 Mask 不同 |
| `_SourceIndirectAlbedoGain`、`_SourceIndirectSaturation` | M[4].z、w | 间接基础色增益与亮度/颜色插值，高 |
| `_SourceRampBias` | G[121].w * G[122].x | 源明暗查表输入偏移，高 |
| `_SourceIndirectStrength` | G[110].z | 源间接色贡献，中；源 3D SH/可见性周边未完全重建 |
| `_SourceDiffuseStrength` | G[110].y | 源漫反组合权重，中 |
| `_SourceSpecularStrength` | G[123].w | 源镜面贡献倍率，高 |
| `_SourceShadowStrength` | G[111].y | 源可见性色组合权重；接独立角色receiver/filter，未分组时回退Unity主光阴影 |
| `_SourceAmbientResponse` | G[27].x × lerp(G[29].x,1,G[122].w) | 源环境响应权重，高；本帧.287722，不可误用1 |
| `_SourceDirectColorWeight` | G[122].y | 原主光颜色响应，高 |
| `_SourceAmbientTint` | Skin的G[113].rgb / G[112].rgb；其他1 | 原fallback环境风格与Unity全局ambientProbe的材质差异，高 |
| `_SourceHemisphereDirection`、`_SourceHemisphereParams` | G[116].xyz、G[117].xyz | 半球方向轴、偏移/缩放/底值，高；轴转为Unity同一基底 |
| `_SourceEnvironmentRotation` | G[126].xy | 源环境反射XZ旋转，高；(0,1)为恒等 |
| `_SourceEnvironmentStrength` | G[110].w | 原环境镜面响应倍率，高；与间接基础色G[110].z独立 |
| `_SkinLightingSdf`、`_SkinRegionMap` | 1082/1101 t20、t21 | 双侧受光SDF、区域R/面部G/染色区域B，高 |
| `_SkinViewTintStrength` | 1082/1101 M[12].xy | 双区域视角染色强度，高；不是GBuffer单一x强度 |
| `_SkinRightOS`、`_SkinForwardOS` | instance[0/2].xyz经场景基底转换 | 解剖右/前轴，中；本次pose网格已烘焙，轴仍随Renderer动态变换 |
| `_SkinSdfBias` | G[126].w × G[111].w | 源SDF明暗偏移，高 |
| `_SkinHemisphereOriginOS` | instance[3].xyz减view[44].xyz，经F/scene origin/B转换 | 面部水平径向半球中心，高；运行随Renderer矩阵变换 |
| `_SkinSpecularMap/Parallax` | 1082/1101 t12、M[17].xy | 唇部等独立高光图与视线局部XY偏移，高 |
| `_ParallaxGlowMap` | 1143 t13 / Resource9182 BC7_SRGB | R高度射线、R视差附加响应，高；masked swizzle写r8.w |
| `_ParallaxGlowParams`、`_ParallaxGlowMap_ST` | 1143 M[12].xyz、M[14] | 射线步数/深度/扰动法线开关、起始UV变换，高 |
| `_ParallaxGlowColor` | 1143 M[13].rgb | 视差附加冷色，高；最后乘基础图Alpha |
| `_ClothAnisotropy` | 1122/1649 M[12].xyzw | 双瓣各向异性宽度、第二半向量偏移、maskG高光重映射，高 |
| `_ClothTangentMode` | M[13].x | <.5取网格切线，否则从几何法线建立水平切线，高；本帧1 |
| `_ClothSecondLobeColor` | M[14].rgb | 第二高光瓣颜色，高 |
| `_ClothCoatSmoothness/Metallic/NormalBlend` | M[15].xyz | coat光滑度、F0金属插值、扰动法线混合，高 |
| `_ClothCoatColor` | M[16].rgb | coat反射颜色，高 |
| `_ClothCoatMaskMap/ReflectanceMap` | 1122 t13/t12；1649 t16/t15 | coat覆盖率R及NdotV²查表反射色，高 |
| `_EmissionMap`、`_EmissionColor` | 1122/1143 t20、M[7].rgb × M[1].w | 普通发光图与增益，高；与599 POM冷色独立 |
| `_SourceOutlineWidth/Depth` | 635 VS slot3[13].xy | 屏幕轮廓宽度/深度增益，高；当前.5/0 |
| `_SourceOutlineSmoothNormal` | 635 VS slot3[14].x | 平滑切线空间轮廓法线开关，高；当前1 |
| `_SourceOutlineWidthMap` | 635 VS t1 / Resource1727219 | R宽度/G深度，高；source sample写zw、resource swizzle=zwxy |
| `_SourceOutlineCoverageMap/Cutoff` | 635 PS t0 / Resource62、slot1[12].x | R覆盖率/.5阈值，高；本帧白图恒通过 |
| `_HairPrimarySecondaryShift` | 1165 M[13].xy | 双发丝偏移，使用前映射 2x-1，高 |
| `_HairPrimaryStrength` | M[13].z | 主发丝高光倍率，高 |
| `_HairSecondarySmoothness` | M[14].x | 次瓣指数 (1-x)*200 后向零取整，高 |
| `_HairFlowDirection` | M[14].y | 对象局部发丝流向，高 |
| `_HairSecondaryColor` | M[15].rgb | 次瓣高光色，高 |
| `_HairDetailNormalScale` | M[12].y | RGBA法线 ZW 层强度，高 |
| `_HairViewAlignmentPower` | M[13].w | 细节法线/视线在解剖XZ平面上的对齐指数，高 |
| `_HairOcclusionMap/ST` | 1165 t12 / M[18] | 第三瓣遮罩R与其UV变换，高；source写r3.w、resource swizzle=yzwx |
| `_HairOcclusionLobe` | M[16].xyzw | 条带频率、第三瓣偏移、光滑度、最小响应，高 |
| `_HairOcclusionResponse` | M[17].xy | 遮蔽后的饱和度响应与条带/贴图混合，高 |
| `_EyeParallax` | 1061 M[12].y | 虹膜视差，高 |
| `_EyeCurvature` | M[17].y | 圆域程序法线 XY 曲率，高 |
| `_EyeIrisTint`、`_EyeScleraTint` | M[15/16].rgb | Alpha/圆域颜色乘数，高 |
| `_EyeReflectionColor`、`_EyeReflectionStrength` | M[18].rgb、w | 反射贴图 alpha 染色及 RGB 增益，高 |

源环境额外参数逐项对应 `SharedEnvironment/GBufferFormula01`：RoughnessRange=M[0].zw，Occlusion=M[1].x，背面=M[1].w，AlbedoUVWeight=M[2].w，MaterialUVWeight=M[3].x，NormalMipBias=M[3].y，MetallicOverrideWeight=M[3].w，BaseBlend/Gain/MetallicOverride/SpecularRoughnessWeight 分别 M[4].x/z/y/w，SpecularBias/MetallicWeight=M[5].xy，LightingWeight/ReflectionMask=M[7].xy，颜色 M[8].rgb，基础色/材质 UV 变换 M[11/12]。这些映射均由相同源算术直接确定。

1190 的 `EffectColor=M[4]`，忽略顶点色 M[1].y，颜色/覆盖率增益 M[1].zw，单色混合 M[5].y，额外 mip M[5].z，隐藏混合 M[13].w，亮部阈值/增益 M[2].yz，预曝光混合 M[3].x，深度淡出 M[11].x，近远区间 M[11].yzw/M[12].x，整体覆盖率来自 M[19] 与实例淡出。其 COLOR 是 Resource54 偏移4的四个255字节，固化为 `(1,1,1,1)`；证据见 `doc/capture/effect1190-constant-color.json`。本帧 VS 参数化简的输出 UV.xy=原 UV、UV.zw=(0,1)，不需要伪造额外网格流。

所有实际材质值由 `pro/Authoring/Tools/build_semantic_material_bindings.py` 从持久化 `Source/Constants` 与 `material-bindings.json` 生成 `pro/Authoring/Extracted/SI1/Source/semantic-material-bindings.json`，主导入器合并资源路径后发布。主光初始化记录为同目录 `semantic-scene-settings.json`。默认值只为材质新建提供可编辑起点，源场景使用 JSON 中的原数值。工具和提取原件置于 Authoring，不是运行时依赖，也不要求 tmp 保留。

JSON中的颜色是源GPU线性值；ShaderLab的`Color`属性仍保留标准Inspector行为。发布边界必须检查`ShaderPropertyType.Color`，将源linear RGB编码到gamma后调用`SetColor`（Alpha原样），因为Unity线性项目会在上传Color属性时解码；普通`Vector`直接`SetVector`。完整Unity截帧077已实证：原肤色(.637597,.376262,.296138)直接SetVector至Color后GPU变成(.3642064,.1168351,.0713414)，水晶冷色(.366253,.487493,.520996)变成(.1104324,.2026473,.2339916)。这是二次解码缺陷，不应调大原数值补偿。纹理sRGB view和静态像素数据不因此改变。

纹理导出另有独立的颜色边界：`doc/capture/texture-export-color-space.json`以源PickPixel/EXR逐点确认599 Base98916、568 Base102012、Hair Base96852的RenderDoc SaveTexture PNG已经是linear像素。因此发布这些PNG时创建线性Texture2D，不能仅因为原SRV是BC7_SRGB就再次硬件sRGB解码。JSON的`srgb`仍记录源SRV，用于来源审计；发布器按导出实际pixelEncoding决定Unity资产编码。此前GBuffer4导出PNG与Unity截图约3/255的比较可能混合了linear导出与display编码，不能单凭该指标认定颜色链已经闭环；几何/UV/图案的定位结论仍有效。

1649的材质由 `build_semantic_layered_bindings.py` 生成同目录 `semantic-layered-material-bindings.json`，几何仍从 `Effects/import.json` 关联；不能错误地改用主GBuffer网格。其它墨纹/粒子层使用独立 `semantic-effect-bindings.json`，避免不同导入器互相覆盖。

## 光照公式的完成边界

已复用的实质数学段包括源漫反能量 `0.96*(1-metallic)`、介质 F0 `0.04*specular`、源 D/V 高光分布（alpha 下界 1/128，2^-14 epsilon，最大20）、真实 Ramp 输入和采样、Ramp色度分离与亮度比恢复、32³基础色 LUT 展开与插值、双发丝高光核、眼睛圆域视差/程序法线/当前相机基底的反射采样。源双瓣各向异性采用原alpha正负宽度、宽度乘积三次方和相等返回1分支，coat另从真实mask与反射LUT建立Fresnel层。主光和所有局部光均使用当前 Unity Light；源码没有捕获灯位置/相机矩阵的固定页。

这不代表全部源 SurfaceLighting 已经等价重构。其它场景可能生效的源 SH 网格、胶囊/接触可见性、复杂环境色组合、实例特效覆盖/染色和局部光专有响应还存在缺口。当前直接漫反组合把这些边界接到 Unity 实时光与阴影，不能以编译通过或相似颜色证明全部还原。新创作材质的通用 GGX 与诊断 NPR 分支不参与上述源角色默认材质。

主光组合已按1019:1035-1106、1082:674-728重组：间接基础色与direct基础色先根据Ramp/可见性混合，再作Ramp保亮，最后乘半球/主光色组合。删除了早期错误的额外`SH*albedo`叠加。半球输入按源家族区分：1019身体视角染色采用水平扰动法线(Nx,2^-14,Nz)，1082/1101按区域在水平径向与水平法线之间混合，1165 Hair按PS78/1121采用主法线图扰动结果，其他当前分支采用几何法线；源屏幕AO producer尚未接入，因此该独立边界取1，保留Unity主光阴影。1082/1101另启用`EF_SOURCE_SKIN`，接真实t20双侧SDF与t21区域控制的视角染色，不把1019整份程序当作同一模型；源面部侧向遮蔽按区域B/G、相机解剖XZ侧向角控制；半球法线按区域G在水平径向与水平扰动法线间切换。1082/1101的粗糙度向.9变化位于375-515的实例特效分支，当前G[120].x=0、instance[13] packed=0、M[5].x=0，条件false；本帧roughness=1-M[0].x=.742直接与源一致，不能另加猜测调制。该未激活实例特效的完整producer仍是将来的扩展项。

1165发丝主瓣同时乘`0.04*maskG`与环境响应，次瓣也乘环境响应；它们不是直接把Ramp作为独立发光加上去。Ramp纵轴使用法线/视线解剖XZ平面的对齐值再乘源M[13].w指数。半向量使用源相机Z轴/主光混合，不是标准V+L。源view[6]与view[0/1/2].z一致，是相机朝后的Z轴，对应Unity view矩阵第2行，不能误用相机look方向。第三瓣已按1165:1219-1276接回：使用M16偏移/指数、条带与t12R遮罩，经主瓣最大值恢复后衰减主漫反，再以M17.x恢复饱和度；它不增加另一份高光。

主表面/coat的半向量与发丝不同：1122:1138-1151、1082:729-743在屏幕AO边界为1时为`normalize(2*C+L+3*V)`，其中`C=normalize(cameraZ.x, L.y, cameraZ.z)`；发丝1165为`normalize(normalize(2*C+L)+V)`。两条路径都读取当前Unity相机Z轴与动态Light方向，不保留捕获相机固定向量。额外局部光当前仍使用标准`normalize(V+L)`，源局部光专有几何响应尚未完整移植。

发丝1268-1270的入射项使用主受光与可见性组合后的镜面辐射响应，而非再次直接乘`LightColor*shadow`。主光函数同时输出漫反结果与此镜面入射项，第三遮罩瓣只修改主漫反，双发丝瓣使用镜面入射项；这使阴影内的源间接响应保持独立，避免重复整项乘阴影。

520/585/599/1649启用`EF_SOURCE_ENVIRONMENT_REFLECTION`，使用原1122:1267-1374的两个有理BRDF多项式、多次散射补偿和`mip=1.2*log2(max(roughness,.001))+5`；不替换成通用split-sum LUT。运行采样Unity逐Renderer的`unity_SpecCube0`并调用Core的HDR解码，静态Cube11550仅作为authoring输入建立原生ReflectionProbe。coat具有独立粗糙度/法线/环境响应。各向异性反射法线已按1122:1298-1312用带符号maskG*M12.x选择T/B，将视线投影到该轴的垂面并与原法线混合；完整环境sum按1449-1452乘源环境色、响应下界.5、G110.w与可见性混合，在direct coat transmission之后加入。ReflectionProbe双探针融合/旋转仍需后续扩展，当前本帧单探针无boxProjection可直接工作。

599（包含角）在1143:309-378还有独立视差水晶分支，不能只按Packed PBR处理。`EF_SOURCE_PARALLAX_GLOW`从原切线基底与当前视线作R高度射线步进，再从最终偏移UV读R（sample目标w、resource swizzle=yzwx，不能误按目标寄存器分量识别通道），乘原冷色M[13]与基础图Alpha。当前捕获的步数1、深度.107、UVST=(0,0,0,0)都直接固化来源值；UV缩放为0仍保留动态视差偏移，不能因此删掉整个分支。它与t20普通Emission、UnityProbe镜面是三个独立项。

1143的s3与普通s1共享Resource61：U/V/W均Wrap、min/mag Linear、mip Point，对应Unity Repeat+Bilinear；SDF/Ramp/LUT的s0为Clamp。视差UV可能为负，因此专有水晶图的重复方式必须随语义纹理发布，不能沿用统一Clamp。

635是真实发丝轮廓绘制，617后59757个索引、CullFront、ZWriteOn，PS只输出RT0黑。`EF_SOURCE_SCREEN_OUTLINE`复用635:189-255与旧OutlineProjection的半FOV atan多项式、VP投影方向、aspect、深度饱和宽度和逐分量最小像素扩张；没有猜世界单位宽度。原v4.xy为切线空间平滑法线XY，Z按sqrt(1-min(XY²,1))重建；617.world2的ts2n与原输入17162顶点逐float32相同，发布为Mesh UV2/TEXCOORD2。法线方向乘当前VP的w=0向量，不能误换纯View，因为635 cb0[32..34]明确含3.185/5.656的焦距缩放。当前摄像机投影负责jitter，源frame[19]捕获抖动不进入运行时。

2026-10-28纠正：不能把源635移到所有表面之前并写五RT零值。原635在617之后、655背景之前，只改RT0，G4逐byte不变，见`../capture/outline635-mrt-comparison.json`。先前增加的Lighting尾部`EndfieldOutlineColor`硬写SceneColor黑色同样不等价；240实际A/B显示关闭它可明显改善头发与额前过黑，故移除此合成路径。

最终通用契约保留七阶段Outline入口；GBuffer内部依次绘制普通前景opaque(queue≤2499)→只绑定RT0+depth的`EndfieldSurfaceOutline`→远景GBuffer(queue2500)。这样轮廓保留先前Face/Hair的其它MRT，外扩区域又可正常挡住随后背景，避免错误继承背景G3/G4。655已从509顶点/2304索引的实际几何确认是半径约25的背景包围球，作者期语义材质设queue2500，见`../validation/source655-background-geometry.json`；不按事件号做运行时调度，也不把真实平台673/1210归成远景包围体。可选深度偏移用当前GPU投影重算NDC；未启用源轮廓的材质保留独立通用世界宽度描边功能，默认0。此前“五RT清零等价”以及“Lighting硬黑合成等价”的结论均撤回。

## 角色独立阴影与接收法线

2026-10-28侧胸/腋下三角台阶的同机位Normal/Shadow/关阴影A/B，将残留定位到独立阴影缺项。源1019并未禁收selfshadow：PS1030读取t4.g，再与BaseAlpha/Ramp组合。新提取903/914证实本帧主cascade分支跳过，角色G来自独立角色map；914按GB3的10bit扰动N执行接收点偏移及16Gather核，不是普通CSM+顶点normal bias的等价替代。

`EndfieldCharacterShadow`声明角色组的当前casters/receivers；投影从Unity当前Light方向和caster bounds动态生成，与观察相机frustum无关。`CharacterShadows.hlsl`输入当前世界位置、GB3等价法线、屏幕像素及运行时组索引。原接收偏移为3/6个X方向worldTexel，沿towardLight/扰动N移动，入射因子使用`1-clamp(dot(N,outwardLight),0,.9)`；worldTexel从当前atlasUV-X矩阵行长度与图集宽度推导，未保存捕获投影矩阵或固定世界毫米值。

角色图使用源D16深度格式，专用Caster无顶点法线偏移、CullOff，raster bias源逻辑8/0。Filter保留真实DXBC16组常量、4×4屏幕旋转、64深度样本及阻挡率/平均深度差的非线性；半径原式为4/atlasWidth标量，2:1图集下保持X4/Y2像素，slot外围guard避免串采其它组。所有数值由离线`characterShadowProfile`固化到运行时组件，运行不读取CB。

GB2保留10/10/10/2载体，actor使用8..23 one-hot，角色0仍为原258；未注册对象清离线actor位，回退普通Unity主光阴影。源角色主光、coat与IBL共用一次actor visibility，环境655/普通材质继续用CSM。Eye的程序化虹膜/角膜法线只参与BRDF，接收偏移使用替换前的GB3法线。281同265近景复拍已消除原侧胸长三角台阶，衣物投影保留；极近软影仍可见源旋转核纹理，不以无来源blur消除。证据和数值证明见`../capture/source-shadow-chain.md`及`../validation/skin-eye-corrections.md`。

## 材质Inspector的语义分组契约

所有local keyword都有对应`Toggle`属性。发布器先按keyword同步浮点值；交互编辑时也必须同向更新，不能让勾选框为0而keyword仍启用。家族`EF_HAIR/EF_CLOTH/EF_FACE/EF_EYE`互斥，适合以一个家族下拉框呈现；不要把四个独立Toggle同时开放成可混选状态。模型入口区分源角色表面、源环境、源效果与通用创作模型，原始材质的语义数值仍可直接编辑。

| 折叠组 | 显示条件 | 参数范围 |
| --- | --- | --- |
| 基础表面 | 始终 | BaseMap/BaseColor、法线、Alpha与裁剪 |
| 物理/风格受光 | 通用创作模型 | Metallic/Roughness/Occlusion/Specular；诊断NPR权重独立标识 |
| 角色受光 | SourceCharacter | LightingRamp、AlbedoResponseLut、PackedMask及间接/漫反/高光/阴影响应 |
| 环境反射 | SourceEnvironmentReflection | 环境旋转；显示使用场景ReflectionProbe的说明，不暴露捕获Cube槽位 |
| 皮肤与面部 | SourceSkin或SourceViewTint | ViewTint、SkinRegion/SDF、双区域强度与解剖轴 |
| 发丝 | Hair | 双层法线、遮罩、流向、双瓣位移/强度/颜色/对齐指数 |
| 眼睛 | Eye | 虹膜/眼白染色、视差、角膜曲率与反射图 |
| 分层衣料 | SourceAnisotropic | 双瓣宽度/位移、次瓣颜色与coat覆盖/反射LUT/粗糙度/法线 |
| 视差水晶 | SourceParallaxGlow | 高度图、步数/深度、UV与附加颜色 |
| 环境材质 | SourceEnvironment | 基础/材质双UV、粗糙度范围、金属覆盖、遮蔽 |
| 效果材质 | SourceEffect | 颜色/覆盖率、深度淡出、溶解与亮部响应 |
| 渲染状态 | 始终 | Cull、混合源/目标、ZWrite、RenderQueue及阴影覆盖功能 |
| 高级映射 | 可折叠，默认关闭 | MipBias、GBufferTag、解码实例字段、解剖轴等来源相关数据 |

三个新特性Toggle名称为`_SourceSkin`→`EF_SOURCE_SKIN`、`_SourceEnvironmentReflection`→`EF_SOURCE_ENVIRONMENT_REFLECTION`、`_SourceParallaxGlow`→`EF_SOURCE_PARALLAX_GLOW`；其余沿ShaderLab原有Toggle属性反射即可。各组只编辑Material，不要求运行时读取Authoring JSON或原CB。颜色Inspector保持Unity正常Color行为，线性源数据转换只发生在离线发布边界。

## 后处理

`Hidden/Endfield/PostProcess` 的 0/1/2/3 是诊断显示、简单 Bloom、简单 blur、GBuffer调试；源场景走 4/5/6/7/8/9。4 为源区间 CoC 与近远半径，5 为源 SceneDisplay，6 为源 Bloom 13点抗闪烁预滤，7 为二项9×9下采样核，8 为 bicubic 上采样，9 只复制线性结果并在最终采样实施可选 flip。10 为可选的源 UI blur，无实际消费者时不生成目标。

源 CoC 来自 SI1_1742：近区间相等或半径零关闭；远区间同理；远 CoC 大于零时优先远值。SI-1 的近景关闭，远景区间 9→20、半径强度1.41。当前 pass4 仍采用单帧采样合成，尚未恢复原近/远分层和历史链，不能当作完整 DOF 相同。

Bloom 阈值直接复用 SI1_1960 的软阈值向量和亮度抗闪烁权重；下采样源权重为 `[1,8,28,56,70,56,28,8,1]/256`，无非线性步骤时合并相邻样本为双线性25点；上采样复用 Core 的 bicubic，与 SI1_2041 的同一数学结构。Scatter=.77，SceneDisplay combine=.36604023 均来自源CB。颜色 LUT 输入保留原 LogC：`log2(max(color*5.55555582+.047996238,0))*.073499784+.386036009`，不拿线性颜色直接裁剪查表。Unity 目标负责最后 sRGB 编码。

LUT 由 `Hidden/Endfield/ColorLut` 实时生成，旧完整算法保留，外部18行改为白平衡、颜色滤镜、通道混合、Hue/Saturation/Contrast、Lift/Gamma/Gain、Shadows/Midtones/Highlights、范围与 SplitToning 参数。八条曲线是输入资产。没有把捕获生成的 LUT 结果或最终显示图当作该 producer 的替代。

UI blur 的源值2.5是高亮限幅阈值，不是半径。它在每个采样限幅后按半字量化，再进行同一9×9卷积；非线性限幅不能随意合并到25点采样之后。SI-1 本次 UI 实际只使用15张静态纹理与场景深度，不消费该 blur，因此管线不为其创建无用RT。
