# 源截帧阶段与重构管线

本表是学习用的功能对应，不是把RenderDoc事件号搬进运行代码。源没有引擎marker，事件区间按实际输出附件、shader和状态归纳；所有EID只保留在离线来源。运行读取当前Unity相机、Renderer、灯光、深度、Volume和ReflectionProbe。

| 源SI-1实际阶段 | 新管线位置 | 对应与边界 |
|---|---|---|
| shadow350/361/372/381/390/400/409/424/438 | Shadow | 按真实对象映射配置Unity投影。424为1649衣料，非635；眼睛、环境与sky壳不盲目投影。源随机alpha覆盖由StochasticShadow语义实现；阴影相机和附件实时生成。 |
| 488–617角色GBuffer，含脸/眼/衣料/角/皮肤/头发 | GBuffer | 保留五MRT的角色payload及深度规则。源附件为20455/20422/20419/20407/20416，分辨率1506×846；新附件按当前相机与renderScale分配。 |
| 635头发外扩黑轮廓 | 前景GBuffer之后、远景GBuffer之前的SurfaceOutline | 真实存在，width=.5，平滑法线流已在617 world2 flags&2。只写RT0并保留其它MRT，bit16保护Face/Eye；此前独立前置Outline和Lighting硬黑覆盖均不等价，已撤回；247实际GPU顺序见unity247-final-order.md。 |
| 655/673等环境GBuffer及936–968全屏光照 | GBuffer / Lighting | 新全屏Lighting读取五MRT与当前灯光/环境。环境输入来自Unity SH/ReflectionProbe；本帧实际fallback环境色与静态预滤波cube作为初始化，不加载源最终光照RT。 |
| 997–1165等角色表面受光，1233–1356表面合成 | Lighting内EndfieldSurfaceLighting | 在可见表面重绘源有效受光公式，保留深度相等遮挡。新体系支持Unity实时灯光/视角；不把源CB矩阵与整屏结果固化为运行算法。 |
| 1190 sky壳、1210台面 | Lighting / EndfieldEffect与场景背景材质 | 原静态源纹理、UV、SDF格网和有效参数语义化；背景属于场景，Game和Scene均应可见。 |
| 1554–1730透明特效、1649受光衣料 | Transparent | 按实际顺序发布稳定renderQueue。1589/1607/1672 ColorMask0并写深度；1649决定白色菱纹，不是假造基础色。soft intersection采本帧opaque-depth独立副本，避免读写同一深度附件。 |
| 1742–1834 CoC、DOF多阶段及历史 | PostProcess的空间DOF | 有效近/远景深参数来自源。当前是空间实现，不宣称等价恢复源全部历史buffer与temporal DOF。 |
| 1871–1950 motion准备、重投影、lock/history、时域上采样/resolve | PostProcess内Unity通用TemporalAA | 明确非等价。源render1506×846、display2560×1440，含多份色彩/权重/亮度/锁定历史与后续锐化；当前TAA主要同分辨率历史重投影/裁剪，未完整移植FSR重建。 |
| 1960–2132 Bloom/LUT等显示准备，2148 SceneDisplay | PostProcess的Bloom、ColorLut、SourceDisplay | LUT由源静态曲线与语义参数实时重生成，运行不导入捕获LUT RT。显示编码边界明确，最终RGB是display编码；source PNG附带alpha不能作为整屏透明度。 |
| 2148之后两段UI、2906 copy、3389最终UI | UI / EndfieldViewportUIRenderer | 原静态图集、语义材质、真实几何与裁剪状态组成camera引用的UIComposition，只在Game绘制。Scene保留场景背景但不叠角色界面。原copy仅Y翻转，和场景左右坐标问题分别处理。 |

## 时序抗锯齿不能称逐项复刻

现有源数据可直接观测：1871从20422解motion到20511；1887联合depth20361、HDR21332和motion20511生成速度/深度等；1932读取RGBAHalf历史20317、速度20523和lock20527；1941读取currentHDR21332、history20321、exposure20325、velocity20523、lock20527并输出20305/20539/20531；1950继续20305到20539的重建后处理。1941 cb0前几行按int解释得到render1506×846与display2560×1440，jitter当前(.34375,-.240740776)、前帧(.28125,-.092592597)，另有phase-count23。

这些观测支持同类FSR时域上采样链，不支持“加一个TAA就等价FSR”。运行TAA保留每相机自己的实时历史、Halton抖动、运动重投影与历史失效管理，源历史图像从未导入运行。当前整合顺序为Unity TAA→空间DOF→Bloom；源为DOF→FSR→Bloom，顺序差异有意保留并已由pipeline代理确认。单帧终图不能验证运动拖影、遮挡显露、锁定、锐化或长期稳定性。

## 判读对比图

final-with-ui源图已经经过SceneDisplay的Linear→sRGB与显示抖动，比较时保留RGB、直接丢弃附带alpha。静态BC7_SRGB纹理的RenderDoc PNG则已经线性解码，这两个PNG的数值语义不同。角色静态纹理用全mip RGBAHalf发布，UI/最终显示按其各自色彩边界处理，不能用曝光或颜色补偿掩盖二次解码。

本轮已记录083与086中间RGB对照。UI几何已接近，角色着色、边缘覆盖及新描边/TAA需以后续实际Unity截图和RDC验证，不能将这些中间图写成最终验收通过。
