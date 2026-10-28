# SI-1 实际图像问题与修复记录

本文件记录已出现的画面偏差。所有PNG来自Unity编辑器真实Camera.Render；源RDC仅提供对照，运行时没有读取源渲染目标。

| 实际问题 | 定位证据 | 修复 |
|---|---|---|
| 前后网格互相覆盖 | Unity RDC中SurfaceLighting的depthOutput为空 | C# SetRenderTarget使用明确RenderTargetIdentifier颜色/深度参数，避免选中mipLevel重载 |
| 发布网格坐标已改但画面仍左右镜像 | CPU资产、源PostVS、当前Camera逐顶点投影一致，实际截图仍旧方向 | 更新现有Mesh时明确Clear/SetArrays/UploadMeshData；不只CopySerialized原生资产 |
| UI字形破碎、上下位置反了 | 实际Game截图185726-054 | 原图在导入边界转换行顺序；UI临时RT的顶点与最终copy统一方向 |
| 整个角色落在阴影里 | RawShadow满片近端深度；排除环境后的隔离图出现真实角色投影 | 根据源shadow draw对应关系配置renderer投影，排除655环境与1190外壳；不是靠提高亮度或调bias |
| 重开场景后环境光参数丢失 | Scene YAML不保存RenderSettings.ambientProbe | 场景EnvironmentLighting组件保存语义环境颜色，启用时写入Unity标准ambientProbe |
| RDC只有后处理尾段，缺少角色绘制 | 074回放仅18个draw；Camera.Render结束不代表独立渲染线程完成 | 在预热后与EndCapture前同步ReadPixels，077实际记录195个draw、319个动作，包含完整场景与UI |
| 皮肤偏橙、颜色发暗 | 077中568的_ViewTintColor实际为(.364206,.116835,.071341)，等于来源(.637597,.376262,.296138)再次sRGB解码；1190同样把.821434变成.640798 | 源语义表始终保存线性GPU值。发布器只对ShaderLab Color属性转为显示gamma颜色后SetColor，Unity上传恢复原线性值；Vector保持原值 |

## 基础色对照

2026-10-27，源 `doc/capture/reference/gbuffer-4.png` 做显示方向的Y校正后，与实际 `tmp/unity/captures/20261026-191002-586/editor-camera.png` BaseColor调试图逐像素比较。

早期只统计源图中RGB色差超过15、最大通道小于250的99,088个彩色角色像素，得到8位RGB平均绝对差 `(3.12,3.43,3.21)`。**这项数值已撤销作为颜色正确性的证据**：后续确认源GBuffer PNG为线性值，而该Unity截图是显示编码，重复解码与最终编码可能相互抵消。几何投影仍有独立PostVS闭环；颜色应以GPU实际数值和相同显示编码的最终RGB对照判断。

实际颜色修复后，Scene无post侧边背景得到213/255，反解线性.665387，与源R11G11B10值.6640625的差异处于8位截图量化范围。源最终UI结果的RGB已经是显示编码，alpha是附带通道，不作透明合成；比较图必须去掉alpha。最新中间对照见 `comparison-086/README.md`。

## 阴影投影对象的来源

源shadow绘制350/361/372/381/390/400/409/438分别对应可见角色488/520/538/553/568/585/599/617；眼睛502、环境655和1190没有对应的shadow draw。原帧另有424投影，已通过完全相同IB/VB闭合到1649受光衣料叠层，其Shadow和Surface的UV逐bit相同；投影保留源sqrt(alpha)随机覆盖算法。事件号只用于离线导入证据；运行时读取Renderer.shadowCastingMode与材质ShadowCaster。

## 白色菱纹的实际来源

原帧1625后的画面仍有深色素面内裙，1649后才出现参考图中的白色菱形/三角纹。它是独立受光的透明覆盖表面，使用One/OneMinusSrcAlpha和写深度；不能通过修改基础色纹理或光照参数在前一个阶段补造。其捕获姿态位置、法线、切线和UV均以实际PostVS恢复，再由当前Unity对象/相机变换参与绘制。
