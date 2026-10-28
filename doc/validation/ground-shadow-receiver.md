# 地面实时阴影接收

SourceBackground绘制源673的真实四点台面几何，Varyings.world来自EFWorldPosition，normal来自模型法线；SDF格网只控制颜色/覆盖，不替代台面空间位置。原1210有效源PS是底图与格网的无光照合成，不能声称它原本包含Unity灯光的完整受光分解。

用户要求新场景正确接收实时投影，因此添加可编辑ReceiveShadows功能。它查询当前Unity主光shadow atlas的EFMainShadow(world)，跟随当前灯光变换、阴影强度及软硬过滤，不导入源阴影RT，不贴屏幕阴影图。

最初直接把整个无光照底图乘shadow会同时杀掉间接环境光，218实际脚印区域变成纯黑。已改为当前真实地面N的EFUnityAmbient(N)作ambient，max(mainLightColor,0)×saturate(N·L)作main，采用(ambient+main×shadow)/(ambient+main)作为逐RGB衰减比，再乘原底图颜色。无有效能量、禁阴影或ReceiveShadows=0时保持原图；没有硬编码灰色阴影强度，也没有额外直接照亮原底图。

当前此台面接收器明确只处理Unity主光阴影。其它方向光、点光、聚光的渲染和接收能力由通用受光材质及pipeline诊断场景验证，不能把台面此处称为多光源受光已通过。后续需以主代理实际截图/RDC核对atlas、接收坐标及颜色结果。

232实际RDC进一步发现地面PostVS法线为NaN，离线673 world2四个normal全零：原unlit源VS没有使用normal，这不是阴影atlas缺失。prepare_background.py现按实际IB三角形面积加权恢复几何法线，转换Unity后约(7.9e-7,1,9.97e-5)，确保NdotL来自真实朝上台面。主代理重新发布后249实际全身截图反馈为正确灰色实时投影；232的旧零N与atlas数值证据在unity232-and-237-rdc.md。
