# 635 实际头发描边

源438 shadow之后、488角色GBuffer之前没有mesh draw，但不能据此判断整帧无描边。真实描边为617头发之后的635：59757个indices、CullFront、FrontCCW=true、深度写入开启、源反向Z比较GreaterEqual，目标仍为五MRT中的RT0=20455。PS只输出RT0黑色，未输出其它MRT。

实际VS为doc/capture/shaders/635_vs.txt，PS为635_ps.txt；真实常量分别在Source/Constants/635_vs_cb3.json与635_ps_cb1.json。VS cb3[13]=(.5,0,0,0)：宽度0.5、深度挤出增益0；cb3[14].x=1使用平滑法线，cb3[10]=(1,1,0,0)为UV变换。不是所有角色都默认开启一个统一宽度。

VS t1为静态BC7_UNORM纹理1727219，LOD0取R作宽度遮罩、G作深度遮罩。DXBC的sample_l目标r6.zw与资源swizzle.zwxy对应最终R/G；不能只看资源swizzle首两个字母便称B/A。实际UV的离线bilinear LOD0采样中，98.82%顶点宽度遮罩非零，均值0.5910，最大1，见outline635-mask-samples.json。这不是只有draw调用而宽度遮罩全零的空描边。

PS t0实际是RID62的1×1白色SRGB纹理，取R后与cb1[12].x=.5比较，当前恒通过。它不是头发基础色的alpha裁剪。PS通过后输出(0,0,0,0)。

## 平滑法线已经在world2内

617的17162个顶点、59757个indices，world2 flags=2。已有ts2n流就是源TEXCOORD4.xy：slot1、stride12、offset8，R8G8B8A8_SNORM，以max(signedByte/127,-1)解码。源vb1的UV0与world2全部float32逐值一致；独立解码的XY与world2 ts2n最大误差0。

该流位于UV数组之后、IB之前，617 byteOffset=823792、byteSize=137296。工具格式为header、position、normal、tangent、UV、可选alt、可选ts2n、indices；不要从整个文件末尾读取ts2n。运行时直接把已有ts2n送Mesh UV2/TEXCOORD2，不需要读取Outline辅助binary。Outline/617中的原VB、辅助流和import.json只作离线来源与验证；prepare_outline_stream.py可重复生成。

给定N、T与tangent.w，平滑方向为T×xy.x + cross(N,T)×tangent.w×xy.y + N×sqrt(1-min(1,dot(xy,xy)))。系数为切线空间值，不随D3D→Unity轴变换直接翻符号。

## 动态膨胀语义

VS 189–243先构造平滑方向，再乘源cb0[32..34]的VP矩阵（方向w=0），取XY归一化；这里包含焦距，不能误用纯view旋转。再乘displayH/displayW的横轴补偿。FOV因子由当前投影矩阵推导，源使用atan近似多项式，当前为约10°半FOV。

rawOffset = projectedDirection × (.392699/fov) × width × saturate(viewDepth×fov×4.583663) × .005。

pixelFloor = min(max(viewDepth,0),1.570796/fov) × (1/displayW,1/displayH)。源240行若abs(rawOffset)<pixelFloor则取sign(rawOffset)×pixelFloor，所以这是逐分量最小像素宽度，不是最大宽度钳制。最后乘widthMask.R并加到clip.xy。源还移除当前jitter，深度挤出项因增益0不启用。运行实现应使用当前Unity对象、相机、投影和屏幕尺寸，不能把本帧clip坐标或固定世界宽度当描边算法。

源描边位于GBuffer内部的具体draw顺序；新管线将它组织为独立Outline阶段。两者不能仅因名称相同便宣称事件顺序逐项等价，仍需最终深度/遮挡与实际截图验证。

## 后续闭环：附件、Stencil与方向

617后与635后G4原始字节的SHA-256完全相同，零像素变化；RT0有710个颜色改变像素。710不是完整fragment/depth覆盖数，黑写黑不会计入。见outline635-mrt-comparison.json与outline635-rt0-changes.png。因此运行修正为GBuffer末尾只绑定RT0及同一深度，不能提前把其余MRT清零。

635 Blend关闭、One/Zero、ZWrite=true、GreaterEqual、depthBias0。Stencil双面相同：Ref36、ReadMask16、WriteMask239、GreaterEqual、PassReplace、Fail/DepthFailKeep。488 Face和502 Eyes先以Ref52、WriteMask255写入bit16；635 Ref&16=0不能通过已置16的区域。其它角色多数Ref36不置bit16，617本身与635同读写规则。真实状态在gbuffer-stencil.json，运行可将这个用途转为ProtectFromSurfaceOutline语义，而不携带源完整字段协议。

617和635的17162顶点、全部IA VB/IB绑定完全相同；实际PostVS UV、世界位置、normal、tangent逐float完全相同，只有clip.xy和motion.xy外扩。不存在额外635基础pose需要换网格。此前平滑normal的XY系数虽然正确，旧packed world2 N/T基方向却有显著误差；新CharacterDirections方向流修正的是该基。不能把正确ts2n系数等同于整套切线基已正确，见doc/validation/geometry-directions.md。
