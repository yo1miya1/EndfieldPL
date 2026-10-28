# SI-1 903/914接收器与372 caster证据

本记录只整理已有最小补取的数据，没有再次回放。数值与shader代理共用doc/validation/character-shadow-receiver.json及character-shadow-kernel.json；本次从原CB逐float和DXBC immediate常量逐uint复核，两份映射均精确一致。摘要、原始文件相对路径与SHA-256在[source-shadow-chain.json](source-shadow-chain.json)。

## 实际链路

903和914写Resource20410（1506×846、R8G8_UNORM），Body1019后续从t4读取其G作为角色屏幕阴影，不等同于直接调用普通主光CSM比较。

903最终G固定输出1；本帧cb3[35]=(0,0,1,1)，主cascade分支因w=1被跳过，R也退化为1。914另以GB2（t5=20419）的10/10/10/2载体恢复角色one-hot组，当前角色索引0，用独立角色阴影图计算G。它的N来自t6=20407的Y-up octahedral扰动法线，不是ddx/ddy几何面法线。两者不能因都写20410就混为同一接收器。

914相关实际绑定：t0=20413深度、t2=1725766角色阴影atlas（原4096×2048 R16深度，采样视图R16_UNORM）、t5=20419角色载体、t6=20407扰动N。t2的Gather采样器是非比较ClampEdge，min/mag Linear、mip Point；原式自己比较64个原始深度，不是硬件比较PCF平均。

## 1024 tile与3/6 texel偏移

| 来源 | 实际值 | 语义 |
|---|---|---|
| 914 PS cb3[218] | (0,0,.25,.5) | 当前组在atlas内的offset.xy与scale.zw |
| cb3[233] | (1/4096,1/2048,4096,2048) | atlas倒数尺寸与实际尺寸 |
| tile scale × atlas size | (1024,1024) | 当前角色实际tile；372 viewport也确为1024² |
| cb3[188] | (.004925072193145752,.009850144386291504,.001641690731048584,256) | depth offset、normal offset、worldTexelX及其它源字段 |
| cb3[203].xyz | (.3032358587,-.4226182997,-.8540738821) | outwardLight，与towardLight相反 |

源矩阵按P.x×row128 + P.y×row129 + P.z×row130 + row131生成tile-local UVZ。X方向世界梯度长度为length(row128.x,row129.x,row130.x)=0.5948516726493835。由投影和tile推导：

`worldTexelX = 1 / (gradientX × 1024) = .0016416907691467547`

它与cb3[188].z相对误差仅2.32e-8；cb3[188].xy除以z分别精确对应3和6 texel。不是把这两个世界数值当独立经验强度调参。

令N为914读取的扰动法线，Lo为outwardLight：

```text
f = 1 - clamp(dot(N, Lo), 0, .9)
receiverP = P - Lo × (3 × worldTexelX × f)
              + N × (6 × worldTexelX × f)
```

root/shader实现讨论中的sourcebackoff仅指第一项沿towardLight的接收位置回退。没有另一个已证实的caster backoff；不能把filter的meanDelta软化响应也称为空间偏移。

## 原始过滤响应

源914使用屏幕像素低2位选择16组旋转；16个Gather读取64个深度。immediate常量按DXBC uint原位归档，避免反编译文本六位小数损失精度。

UV半径为`4×cb3[233].x`，同一标量用于两个UV轴。本帧它等于.0009765625，在4096×2048全atlas上是X约4像素、Y约2像素，不能误写成每轴分别乘其texel倒数。原式对每个depth计算delta=sampleDepth-receiverDepth，统计delta>=0的阻挡数k与正深度差sum；receiverDepth先限制到至少.01。

令x=k/32-1、t=1-abs(x)、r=saturate(sum/(k×receiverDepth))，响应化简为：

```text
transition = lerp(t³, t, r)
visibility = .5 - .5 × sign(x) × (1-transition)
```

无阻挡者为1、全64阻挡为0、32阻挡为.5；运行实现应显式处理k=0，不依赖0/0。它同时依赖阻挡率与相对平均深度间距，不能替换成k/64或普通9-tap Tent。

## 源372 caster

372与身体538的原IB、POSITION/UV/蒙皮权重索引VB绑定一致。VS虽计算posed N并输出o2.xyz，最终SV_Position(o6)却只由世界位置乘cb2 shadow矩阵生成，没有顶点normal displacement。PS为空、无SV_Depth覆盖，也没有Geometry/Hull/Domain阶段继续偏移位置。

实际光栅为CullOff、DepthBias=-8、SlopeScaledDepthBias=-0.0，深度GreaterEqual且写入。普通URP式vertex normalBias是另一条caster路径，不能默认1/1便宣称等同源。新独立角色caster需与普通CSM caster分开；随机alpha覆盖子件仍保留真实sqrt(alpha)与屏幕dither，不以不透明占位替代。

## 运行边界

这些是离线来源证据。新实现使用Unity实时Light、角色组包围体、当前世界位置/N、实时独立角色map及动态矩阵；worldTexel由当前投影计算。原20410屏幕结果和1725766深度atlas不导入运行，也不把源绝对世界矩阵或pose参数作为shader调度协议。当前通用CSM/附加灯仍保留自己的实时功能，不与此角色专用接收器混称逐算法等价。最后须用新Game RDC确认专用pass、atlas、角色ID载体和接收参数实际GPU绑定。
