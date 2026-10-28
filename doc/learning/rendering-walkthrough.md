# 从场景到最终画面

先打开 `pro/Assets/Endfield/Scenes/SI1.unity`。Hierarchy中的Character是捕获姿态模型，Environment包含台面和Unity环境光配置，Key Light是真实方向光，Post Process Volume控制后处理，Main Camera最后附加视口UI。所有这些都是保存后的Unity对象，显示场景不需要原RDC或生成器。

## 按一次相机绘制阅读

1. `EndfieldRenderPipeline.Render` 取得Unity相机剔除结果，为该相机更新自己的VolumeStack。
2. `EndfieldScriptableRenderer.Render` 创建本相机临时附件并调度七个Pass。每个Pass只使用当前帧数据，附件在相机结束时统一释放。
3. Shadow通过Unity阴影剔除和Renderer的投影开关产生实时阴影。是否投影是场景对象属性，不能因为一个Mesh能显示就默认让它投影；大背景壳会遮住整个人物。
4. Outline和GBuffer共用深度。通用挤出轮廓在前；源屏幕轮廓在GBuffer阶段按“普通表面→只写RT0的轮廓→queue2500远景包围体”执行。五张GBuffer保存基础颜色、法线和源模型payload；轮廓不清空法线/材质附件，也不额外在Lighting覆盖整块黑色。
5. Lighting先处理可延迟求解的表面，再绘制有 `EndfieldSurfaceLighting` 的可见表面。SI-1的角色仍需要逐材质纹理、Ramp和专有模型，所以保留这条混合路径；不会把源实例payload硬解释成金属度。
6. Transparent按透明排序绘制台面和特效。源帧有写深度的前向表面，也有透明混合效果；队列、混合、剔除和深度状态由材质决定。
7. PostProcess先用每相机独立历史、当前/上一帧Unity变换做时序抗锯齿，再从Volume取得曝光、景深、Bloom和显示映射。SceneView与Game都执行它。UI只叠到Game最终结果，调试附件时跳过UI以便看清内容。

## 修改效果的位置

- 转动Key Light或修改颜色、强度，改变真实入射光；阴影会由新的灯光变换重新生成。
- 移动Main Camera或在SceneView观察，视线方向、投影、当前世界位置均来自Unity；源相机常量没有写死进Shader。
- 修改Environment上的 `EndfieldEnvironmentLighting.linearAmbientRadiance`，改变Unity标准ambientProbe。源常量只在生成场景时初始化此语义颜色，场景组件保存它以便重开后继续有效。
- 修改角色Material的语义参数和纹理。命名映射文档给出原常量槽位、分量及推断依据；对照复刻时应保持实测值，学习实验可另存材质副本。
- 材质Inspector先选择互斥着色模型，再展开相应功能。未启用的家族参数不占据主面板；渲染状态单独设置。运行时不需要生成器来解释这些参数。
- 修改全局或局部Volume来观察后处理。UI不会重复经过曝光和Bloom。

## 加一个新的渲染阶段

在 `Runtime/Rendering/Passes` 新建小型Pass，明确读写附件；在 `EndfieldScriptableRenderer` 顺序表中插入。需要额外临时图时由本相机的资源对象申请，消费后随相机释放。不要向运行代码增加捕获事件号表，也不要把材质差异放进C#调度器。

## 换角色时做什么

角色流程导出模型后，先在Authoring中解释源材质和状态，生成语义绑定。蒙皮后的姿势法线、切线和handedness必须与实际PostVS对应；仅位置正确不能保证光照和视差正确，见`../validation/geometry-directions.md`。发布器把输入变成独立Mesh、Texture、Material和Prefab；运行管线继续处理普通Renderer。源事件号用于离线配对和证据追踪，不作为运行时分支条件。

捕获姿态不等于动画系统；当前网格没有被当作可动画骨骼模型。新管线使用Unity风格TAA和原生前帧对象矩阵，原游戏的FSR式时序上采样并未按原lock/reactivity历史逐项复现，透明效果运动也尚未完整接入。实时主光级联、额外方向光、点光六面和聚光阴影已通过多光源场景与GPU截帧验证，见`../rendering/multi-light-demo.md`。切镜时调用相机设置的 `ResetTemporalHistory()`；最终近景/整帧截图预热32帧，首次多光源六组对比为16帧。
