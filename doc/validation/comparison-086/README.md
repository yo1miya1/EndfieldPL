# 086 高精度全mip更新后的中间对照

本轮仍非最终验收。输入为2560×1440源final与1506×846 Unity086，使用同一[RGB比较脚本](../compare_rgb.py)，源Lanczos缩小一次，不进行配准、曝光拟合或alpha合成。[RGB并排图](side-by-side-rgb.png)与[完整数值](metrics.json)保留当前状态。

| Ink区域 | 083 MAE | 086 MAE |
|---|---:|---:|
| 左长笔画 | 5.09 | 5.12 |
| 左上结点 | 9.72 | 9.79 |

57张全mip线性RGBAHalf发布后，两个Ink区域没有出现可测的整体改善；上述差异还包含略亮的背景。不能因此认为mip无用，也不能认为完整mip已经解决覆盖差异。UI仍为同几何，五处局部梯度最佳整数偏移均(0,0)，不重复对面板做位置调整。

本轮发现并修复一处有明确来源的采样错误，修正尚未包含在086图内：生成器此前把RenderDoc AddressMode=3误认为ClampBorder。实际本机API枚举为ClampEdge=3、ClampBorder=4；本帧Ink所有实际纹理采样器只含Wrap和ClampEdge。1571/1589主纹理为U ClampEdge、V Wrap，1693主纹理相同，1730主纹理为U Wrap、V ClampEdge。错误黑边界模拟会额外衰减边缘覆盖。

已移除InkEffect中的黑边界乘法，改为每张纹理自己的原生采样器。离线语义绑定明确发布wrapModeU、wrapModeV和filterMode=Bilinear。源min/mag均Linear，mip均Point，必须保留这种过滤组合；不以重生mip或改变材质alpha补偿。枚举证据为doc/capture/renderdoc-enums.json，各真实sampler在EffectsNative/bindings。

ClipOnly三层1589/1607/1672原ColorMask=0、ZWrite=true，源裁剪阈值分别0.56、0.5、0.56；当前公式中的顶点颜色、LOD覆盖、soft-depth与clip顺序已逐段核对，无依据不改阈值或写深度状态。七个四纹理源PS不读取cb3[22..30]，本帧未启用额外材质渐变页；可见渐变来自源PostVS o5，已经以float4颜色导入。当前动画速度仍为0，不能把差异直接归因于运行时刻。

源还存在1871–1950时域上采样/历史lock链，Unity通用TAA的实现由pipeline代理接入；两者并非同一算法。原历史RT不进入运行资产。待正确采样器与TAA发布后再用后续实际图核对覆盖，避免把多个尚未发布的变化提前计作修复结果。
