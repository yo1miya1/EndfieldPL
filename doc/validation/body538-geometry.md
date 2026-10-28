# 身体538位置与索引核验

本轮只读取已有538/1019完整PostVS、原RDCI与原IB，未重新打开源回放，未改模型、未RecalculateNormals。

- 原始身体5553顶点、27468索引、9156三角形。world2的uint32索引与原draw的uint16索引逐值完全一致，范围0–5552，5553个顶点全部使用，baseVertex=0、drawIndexOffset=0。
- 旧rdc2dcc在读取同一原IB时保存的5553行clip位置，与新完整538 PostVS逐float完全相同。此项连同vertexCount、全部UV逐值配对，支持原IB与PostVS行索引的关联，不能只凭UV相同便下结论。
- 538 GBuffer与1019 Forward的o2世界位置、clip位置和UV也逐值完全相同，排除这两个阶段混用不同pose。
- 使用SceneBuilder.ReadMesh同一placement与MultiplyPoint3x4链，再变回源D3D空间并投影，最大NDC误差为x=1.14e-7、y=4.99e-7、z=4.60e-9。当前世界位置与真实o2最大距离0.000656，源VS166–167会把jitter加进clip；rdc2dcc拟合的正是带jitter的clip位置。差异对应约(.34378,-.24044)像素的全局微偏移，不是局部三角pose错位。

因此本轮没有位置、顶点顺序或拓扑错误的证据，不生成无必要corrected position/index流。原始重复位置确有部分不同源法线，但这不是新发现的导入缝；按主代理要求停止扩查，不能用它替代当前画面问题的A/B证据。

主代理268Normal显示连续、269Shadow明确出现台阶、270关闭阴影后台阶消失，已将当前用户可见问题定位到阴影。此离线几何核验与该结论相容，不应再通过重算法线或改网格掩盖阴影偏移/过滤问题。

完整数值在body538-geometry.json。可重复脚本pro/Authoring/Tools/verify_body_geometry.py只依赖稳定Authoring来源：GeometryValidation/538中的原IB/RDCI、CharacterDirections/Native中的实际PostVS及Source/world2，不依赖tmp会话。
