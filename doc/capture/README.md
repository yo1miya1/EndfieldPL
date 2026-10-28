# SI-1 真实回放与资产来源

本次只读输入 `src/SI-1.rdc`，313,257,758字节。独立ASCII副本与源SHA-256一致：`e2c40a194bf57fe4827aa631a4a50562c792258a2007819d2c1d3f6745ef3bec`；记录见 `capture-integrity.json`。实际MCP初始化协议为2025-03-26，服务自报1.0.0，tools/list已按真实schema使用。回放D3D11成功、degraded=false，267动作、174 Drawcall，最大EID3401；不是3401个动作。无引擎marker，不把输出附件分段冒称原生Pass。

角色主渲染1506×846，最终画布2560×1440。GBuffer角色主要事件488–635，五MRT为20455/20422/20419/20407/20416。936–968等光照后，997–1356为主表面/合成，1404–1730为后续透明/特效，1742–2148为后处理；2148之后两段UI经2906拷贝。参考原图在 `reference/`，保持RenderDoc导出方向：1356/2148图像上下倒置，最终3389方向正确。

## 几何与语义资产

`pro/Authoring/Extracted/SI1/Source` 保存角色FBX、world2、camera、真实bindings、380份已解码CB和DXBC反汇编。源几何来自rdc2dcc的character流程，所有部件和相机采用统一character origin。不是用另一个角色替代，也不是缺UV/normal的VS-out OBJ。

553子件未通过原solver拟合，已用该draw的完整PostVS恢复594顶点/266三角形、UV、世界法线和切线，再写world2/FBX。原证据和补件输入已归档到 `CharacterSupplement/553`，脚本在 `pro/Authoring/Tools/restore_character_submesh.py`。材质585 PS CB2的同事件Resource34551、offset13568、112字节与解码28个float逐值完全一致，见 `cbuffer-crosscheck.json`。

`Effects` 的world2来自真实PostVS posed geometry，保留4组UV及源o5 float4颜色。1649是专用受光衣料层，使用实际o3法线/o4切线，不能套普通粒子。1625→1649逐draw参考明确显示最终白色菱纹在1649出现；source shadow424也对应此几何。后续1693为边缘墨纹、1712/1730为流光，不能把衣料图案差异误归因于585主表面。

`Background` 为源673/1210大台面，四点实际UV已补，SDF纹样使用当前Unity相机viewDepth。`UIPrepared` 为95个真实UI draw和15张静态源图集，7个材质族已拆为93行可读参数；运行无捕获CB数组。最终UI位置、方向与字形已经主会话真实截图确认，后续记录见 `doc/validation/image-corrections.md`。

## 坐标与光栅证据

- 599的4792个顶点：world2→placement→逆场景帧→源VP，与实际PostVS NDC最大误差X=`6.53e-8`、Y=`3.84e-7`，见 `599-postvs-coordinate-check.json`。没有额外X反射。之前左右显示错误的GPU缓存根因已由主会话修复，不再以VP首行符号代替闭环。
- world2 IB与原始IB相同；仅FBX writer另写 `(a,c,~b)`。不能给world2无条件反绕序或反切线w。总变换det与source raster FrontCCW均须纳入实际GPU正面约定。
- UI copy2148/2906的VS常量只体现Y翻转，未见X翻转；UI临时RT、静态PNG行序与场景坐标分别适配。
- shadow424与1649 IB及前三VB资源/offset/stride一致，不是635。485顶点ShadowUV与surfaceUV逐bit相等，见 `shadow424-bindings.json`、`shadow424-uv-check.json`。424 CullOff，实际coverage为sqrt(t0.a×1)与源屏幕噪声比较，已移植StochasticShadow。

## 环境与覆盖边界

Cube11550为BC6_UFLOAT静态环境，完整6face×8mip已导EXR与float32 RGBA blob，未重生mip。原mip0平均RGB约(.911,.925,.916)、最大4296，不是黑图；统计在 `cube11550-statistics.json`。六份SH 3D volume另有全体素DDS归档，但本帧角色走实际fallback环境色分支，不因资源存在而启用volume。

颜色边界已用实际GPU像素定位：BC7_SRGB原资源经RenderDoc导出的PNG存线性解码值，再以sRGB导入会二次解码。599/568/Hair520的九处彩色探针与EXR逐值一致，见 `texture-export-color-space.json`。为保留暗部精度，全部57张语义绑定静态纹理另导全mip线性RGBAHalf，索引在 `pro/Authoring/Extracted/SI1/TexturesNative/index.json`；保留原SRV证据但不按其标签二次转换。

LUT20329、HDR20539及2148显示输出仅在tmp做诊断，不导入运行。最终场景使用本帧Unity相机/灯光/深度/ReflectionProbe与重生成后处理。离线来源、工具与运行资产的发布顺序见 `pro/Authoring/README.md`。

本次导出的原始模型为截帧姿态，未恢复角色动画、UI交互或跨帧时间稳定性。没有GPU计时，不据几何量宣称瓶颈。MCP回放已close_capture，session_status明确isOpen=false；native导出器均在finally关闭controller/capture，遗留的本任务qrenderdoc错误会话也已关闭。
