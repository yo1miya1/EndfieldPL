# 角色局部阴影

SI-1 的角色阴影与普通场景级联阴影是两条路径。914 把独立角色投影的可见性写到屏幕纹理 G 通道，1019 等角色光照程序读取它；本帧级联分支被关闭。直接用普通级联 PCF 替代该 G 通道，会丢失角色投影的接收偏移和过滤方法。侧胸三角明暗问题由这项缺口触发，不能通过重算法线或调整肤色修补。

## 场景里的组件

`EndfieldCharacterShadow` 放在角色根节点，显式保存 `receivers` 和 `casters`。前者决定哪些 Renderer 接收该局部阴影，后者决定哪些 Renderer 生成投影。两组可以不同，例如眼睛接收阴影但不投影，隐藏的遮蔽网格只投影。发布场景与 Prefab 持有组件和引用，运行时无需 Authoring、RDC 或导出 JSON。

投影方向来自当前 Unity 主方向光，投影范围来自当前 caster 的世界包围盒。它不绑定观察相机；Scene 与 Game、相机平移或转动均使用由同一组物体和灯光确定的投影。移动物体、旋转灯光或改变投影对象会重新生成相应数据。

每个组取得一个运行时索引，通过 `MaterialPropertyBlock` 传给 Renderer。GBuffer 保留原来的 10/10/10/2 载体和材质标记，角色位改由组件索引生成。最多 16 个角色组使用位 8..23；不使用固定来源事件号匹配角色，也不以空间包围盒重叠来猜接收者身份。

## 参数为什么是这些值

| 组件参数 | SI-1 语义与来源 |
| --- | --- |
| `resolution = 1024` | 914 的 atlas 尺寸与 tile 矩形相乘，实际 tile 为 1024×1024 |
| `depthBiasTexels = 3` | 914 CB3[188].x / .z = 3，接收点向光源偏移 |
| `normalBiasTexels = 6` | 914 CB3[188].y / .z = 6，接收点沿当前扰动法线偏移 |
| `filterRadiusTexels = 4` | 914 过滤核使用 4 / atlasWidth 的 UV 半径 |
| `rasterDepthBias = 8` | 372 的 reverse-Z 光栅偏置为 -8；通过 Unity 的逻辑深度偏置接口适配 |

CB3[188].z 并非未解释的世界常数：它等于 `1 / (投影 UV 的 X 方向世界梯度长度 × tileWidth)`。运行时每帧用新投影推导世界纹素尺寸，再乘 3/6；没有保存捕获时的固定毫米偏移、灯光矩阵或阴影图。

源 914 使用 GBuffer 解码后的**扰动法线**，不是旧工程另一变体中用屏幕导数求出的三角面法线。源投影的 outward direction 与 Unity toward-light 方向相反；换算后接收位置为沿光源方向的偏移加沿法线的偏移。角度权重仍按源公式计算。

源 372 的 caster 没有顶点法线偏移，因此独立的 `CharacterShadowCaster` 直接投射当前世界位置，并保留覆盖率裁剪。角色深度图沿用实际源 D16 格式；固定光栅偏置 8 在 D16 和 D32 float 上代表不同深度距离，不能只复制数字而忽略格式。场景 CSM 与附加灯仍保留 Unity 风格 caster bias，二者不混用。

## 过滤与边界

`CharacterShadows.hlsl` 保留源 16 组圆盘采样，每组 Gather 4 个深度。64 个样本的阻挡比例和平均深度差共同决定可见性，这与 PCF 硬比较平均不同。原始圆盘常量按 DXBC 位模式保留，参数与计算有独立函数和注释。

局部图包含组件明确列出的 caster；需要某个外部物体遮挡角色时，应把它作为该组投影输入。普通环境接收面继续使用主级联阴影，点光、聚光和附加方向光继续使用相应 Unity 阴影图集。角色组未绑定时，角色光照回退普通主光阴影。

原始证据见 `../capture/source-shadow-chain.md`，偏移推导见 `../validation/character-shadow-receiver.json`。281按用户侧胸机位复拍，原长三角台阶消失且衣物遮挡仍在；近距离过渡仍可见源4×4旋转核的采样纹理。282完整GPU截帧确认D16图、实际receiver绑定和矩阵一致性，见 `../validation/unity282-character-shadow.md`。修复没有改变源身体网格、肤色或材质粗糙度。

## 已执行的同机位隔离

原始侧胸Final265与Shadow269具有完全相同的view/projection，Shadow调试中直接出现与皮肤一致的长三角阶梯；关闭阴影270后明显消退。该调试是全屏深度重构采样，不经过SurfaceLighting的ZTest Equal，因此本轮没有修改表面深度测试或顶点计算。

Unity CSM偏置1/1和depth1/normal0分别在275/277以相同矩阵临时测试，大片阶梯仍存在，未把这些参数永久写入主灯。第一次273受到DomainReload后SceneView临时camera归零影响，已排除，后续使用265的完整相机证据恢复精确矩阵。

281重新发布独立角色组后，Final `20261028-152231-124`和Shadow `20261028-152231-289`中的大片侧胸三角台阶消失；相机矩阵仍逐float匹配原265，主Light偏置仍为原值.03/.12。投影对象和接收对象均由场景/Prefab的组件引用保留，未调整肤色、材质法线或光照强度来掩盖差异。各对照路径、图像哈希与矩阵核对见`../validation/skin-shadow-isolation.json`。完整Game与GPU资源审计另由最终验收记录补充；近景仍可见源4×4屏幕旋转采样的细颗粒，不等同于原先沿几何三角边界的大阶梯。

## 当前模块边界

只有`casters`中启用、激活且ShadowCastingMode非Off的Renderer参与包围盒拟合；其材质还需提供`CharacterShadowCaster`专用Pass才能绘制。Pass直接使用当前位置，CullOff、D16、逻辑raster8/0；覆盖率和随机裁剪仍由材质控制。没有专用Pass的第三方材质不会自动借用CSM的带法线偏置Pass。

共享图集最多16组，采用2:1比例；每组有效viewport为请求的统一最高分辨率，外围另有6像素保护区（默认radius4时），不会从1024有效像素中扣除边缘。投影XY/Z覆盖显式caster的世界Bounds并留出接收偏移和过滤余量；观察Camera不参与拟合。当前只为主方向光提供此角色局部路径，点光/聚光和额外方向光仍使用已验证的普通Unity阴影图集。
