# 侧胸caster法线与真实面法线

本轮不改runtime、不重算法线。以275实际相机/evidence投影身体538，在1200×900画面中选侧胸ROI(x350–800,y380–800)。选择是三角形中心投影与几何朝向筛选，未重建其它衣料遮挡，不能将其称为逐像素可见性查询。原始相机与模型数据均在稳定Authoring目录，脚本verify_body_shadow_normals.py可重复生成JSON。

ROI共143个候选三角形，其中几何朝相机43个。对这43个，faceN·平均posed shadingN的最小值0.9026、中位0.9947；夹角中位5.92°、90分位13.41°、最大25.50°。逐corner与对应面法线的夹角90分位22.79°、最大49.51°。该区域没有平均N反向，不支持整体winding反号或严重艺术法线改写的解释；它是低面数模型上正常但不可忽略的平滑法线偏离。

当前主灯下，这43个面的几何NdotL中位为-0.2569，90分位仍为-0.009，主要处于背光/终止线附近。涉及46个顶点，URP式normal-bias因子1-saturate(NdotL)中位为1、范围约0.542–1，属于满normal-offset敏感区。因此normalBias改变caster形状和自阴影具有明确机制；并不需要把normal本身当成损坏模型重算。

当前ShadowVertex只取EFVertex的世界位置与normal来做偏移，tangent/Tw不参与caster位置计算。Tw错误会影响其它切线空间着色，但不能直接解释Shadow调试视图中的三角阶梯。

## 源372的实际差异

经授权只补取源372/903/914，同一回放成功导出shader、实际CB与必要绑定，未跑全帧流程。BodyShadow372的VS确实计算蒙皮法线输出o2.xyz，但最终SV_Position(o6)只由posed world position乘cb2[0..3] shadow矩阵生成，完全没有normal相关的顶点位置偏移。其PS为空、无SV_Depth覆盖，无Geometry/Hull/Domain shader继续修改位置。

源光栅CullOff、DepthBias=-8、SlopeScaledDepthBias=-0.0，反向Z GreaterEqual且写深度。源身体caster不等价于当前URP depthBias+vertex normalBias方案；Depth1/Normal0隔离有来源依据。仅把Light调成URP默认1/1不能证明忠于源。903/914接收器的实际producer逻辑由shader代理依据同批数据核对，不能靠持续试bias值代替。

372与538的原IB绑定完全一致，实际POSITION、UV、蒙皮权重/索引所在VB slot0/1/2也完全一致。只有372未消费的slot4不同；不能将整个vertexBuffers数组不相同误判为换了shadow mesh，亦不能将未读取的Tw归为caster偏移来源。

原始程序位于ShadowReceiverNative/programs/372-Vertex.hlsl，状态在graphics/eid-372.json；903-Pixel.hlsl、914-Pixel.hlsl及各自CB/绑定同批保存。完整法线分布与normal-bias因子在body538-shadow-normals.json。没有采用新的corrected geometry或RecalculateNormals来掩盖此阴影问题。
