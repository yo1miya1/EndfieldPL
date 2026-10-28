# Unity实时多光源与阴影示例

编辑器入口由普通Unity灯光、网格、材质和Volume构建场景，没有来源CB或固定light矩阵。主`SI1.unity`的source灯光保持独立。

1. 调用`Endfield.Editor.EndfieldLightingDemoBuilder.Build()`，生成`Assets/Endfield/Scenes/MultiLightDemo.unity`。Builder以Additive临时场景保存，结束恢复原活动场景和运行时环境SH。
2. 如需检查同一组灯对角色材质的效果，调用`BuildWithCharacter()`，生成`MultiLightCharacterDemo.unity`。该版本实例化已发布的普通SI1 Prefab；基础Demo不依赖它。
3. 打开`MultiLightDemo.unity`，调用`Endfield.Editor.EndfieldLightingStudy.CaptureLightingStudy()`。该方法只操作当前Demo里的真实Light组件，结束恢复enabled/shadows，不触碰主场景。

一次Study依次输出主方向光、主+蓝色点光、主+暖色聚光、主+补方向光、全灯、全灯但关闭阴影六种状态。相机位置相同，1920×1080、各16次Camera.Render预热。每图JSON保存灯类型、enabled、颜色、强度、范围、锥角、位置/旋转、shadowStrength、bias和normalBias；全灯状态额外请求一份真实Unity RenderDoc。结果在`tmp/unity/lighting-study/<时间>/study.json`及同目录PNG/JSON，实际RDC路径记录在all案例的capture目录。截图工具属于Authoring，可整目录删除；普通Demo Builder保留在Endfield/Editor。

示例的灯强度和颜色是独立教学配置，不是给SI-1补光。地面为普通HybridLit，展示真正BRDF照明和实时接收；source台面是unlit底图的shadow-catcher扩展，两者不能混称同一材质。

## 运行时契约

- 主方向光：优先当前可见的RenderSettings.sun，否则选择最亮方向光；Unity原生4/2/1级联。
- 额外方向光：独立单张正交shadow slice；点光六面；聚光单张透视slice。所有矩阵与split由Unity Compute*ShadowMatricesAndCullingPrimitives生成。
- 每相机一次CullShadowCasters提交所有灯的split范围，RendererList使用该灯内部splitIndex。没有按截帧事件调度caster。
- 光照和阴影用同一个额外灯顺序：排除main，保留当前可见directional/point/spot，最多32。directional位置w=0，local位置w为逆范围平方。
- 额外阴影Atlas只在实际有请求时申请，按slice数量均分方格；无额外阴影时强度数组全零且绑定有效fallback深度。所有临时Atlas在当前Camera finally释放。
- 硬阴影使用Unity比较采样器；软阴影复用Core Tent5×5九次双线性比较，采样限制在各slice边界。point六面按Unity CubemapFace选面，FOV接缝保护角、Y基底修正、偏置与point normalBias=0沿本机URP实现。
- `additionalShadowAtlasSize`决定共享Atlas质量。当前不提供URP那样的每灯分辨率优先级打包、ShadowMask或光层接收过滤。

## 这组实际验收需核对

1. 六张图点光的蓝色范围、聚光的暖色锥体、补方向光和全灯合成有实际变化；all与no-shadows只改变遮挡，不改变灯位置/强度。
2. 主CSM有caster；全灯额外Atlas有8个slice请求（point6+spot1+补directional1），允许看不到caster的cube面为空。不能要求六面都有物体。
3. receiver PS真实绑定两张深度Atlas、额外world-to-shadow矩阵/强度数组；点光每面caster globals包含该Unity Light的位置，spot与directional方向随Transform变化。
4. 主场景的足底台面现在实际采样主光阴影；关闭接收或主光shadowStrength会移除该影。source台面保留Unity环境SH与直光能量比例，避免把unlit底色直接乘成纯黑。
5. 修正导出法线/切线后，再判断颈腿块状明暗是否来自shadow bias；不能用光强或任意阴影颜色掩盖方向流错误。

## 已执行的一次六图验收

Root在真实Unity编辑器执行了通用场景`20261028-135957-519`和角色场景`20261028-140523-418`两组Study，均为1920×1080、16次预热。每组相机位置/旋转完全相同。下表统计最大RGB通道差至少8/255的像素数，基线为各组仅主灯图；它衡量可见灯光变化，不是源画面还原分数。

| 状态 | 通用场景变化像素 | 角色场景变化像素 |
|---|---:|---:|
| 主+点光 | 331940 | 681019 |
| 主+聚光 | 72422 | 309441 |
| 主+补方向光 | 844449 | 603215 |
| 全灯 | 951018 | 984241 |

全灯与全灯关闭阴影直接比较：通用场景105529像素变化至少8，最大通道差136；这些像素全部在关影后变亮。角色场景329402像素变化至少8，最大差222。原始JSON、PNG哈希和完整统计分别见`doc/validation/multi-light-study.json`、`multi-light-character-study.json`。

真实全灯RDC的Lighting447绑定两张2048² R32深度Atlas；AdditionalCount=3，额外参数三行分别为(1,1,0,0)、(1,1,1,0)、(1,1,2,1)，对应补方向光slice0、聚光slice1、点光六面slice2～7。有效矩阵数为8，512² tile的实际caster draw存在，两张Atlas深度均非零且有限。证据为`doc/validation/multi-light-gpu.json`及其原始JSON链接。回放已关闭并核对isOpen=false。

第一组示例原偏置.05/.2在曲面上出现轻微self-shadow facet，关影后消失。该值是示例配置，低于本机URP `UniversalRenderPipelineAsset.cs`原生默认depth/normal各1.0。Builder现已采用标准1/1；root重建后只复拍各场景all一次，通用图`20261028-141406-661`中的胶囊顶端原可见facet已消失，投影仍保留，角色图`20261028-141410-708`也保留多色光照及不同方向的影。完整哈希和限制见`doc/validation/multi-light-bias-validation.json`：最终两图32次预热，原六图16次，未把像素差全部归因于偏置；不修改source主灯、不通过全局阴影染色或额外接收偏置掩盖。

Source台面另有独立几何根因：673原离线法线四点均为零，之前unlit路径不消费它；shadow-catcher的NdotL因此为零，直接/间接能量比抵消了阴影。该导入现在按实际IB面积加权生成真实朝上法线。重新发布后的实际Unity近景`tmp/unity/captures/20261028-141055-918/editor-camera.png`已清楚显示角色脚下及衣摆投向台面的动态主光影，环境分量仍保留灰度；没有用台面shadow tint补救零法线。
