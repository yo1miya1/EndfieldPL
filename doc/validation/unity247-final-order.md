# 247最终Game帧的最小补验

实际Unity截帧为tmp/unity/captures/20261028-141049-863/editor_capture.rdc，已先复制为独立ASCII工作副本并核SHA-256。完整哈希与事件摘录在unity247-final-order.json。本轮只检查新描边/远景顺序及保存后的UI，不重跑已由232/237核对的TAA与阴影数据。

实际327个actions、184个draw。GBuffer阶段322–590内：

1. EID401：59757 indices的头发普通GBuffer，绑定全部五MRT。
2. EID542：同59757 indices描边，只绑定RT0=69448与原深度。
3. EID578：2304 indices的远景655，恢复全部五MRT。

因此GPU顺序为角色GBuffer→单RT0 SurfaceOutline→远景GBuffer，描边不会再把其它MRT清零，远景也在其后补齐。Lighting590–Transparent980之间相同59757 indices几何只有743一个正常头发表面绘制，已无此前额外OutlineColor向场景颜色硬写黑色的draw。Stencil保护、主阴影及TAA的实际状态沿用232记录；本轮没有以文件代码替代已完成的GPU核验。

UI1798–2995共有97次实际draw：95个源UI网格，加1812初始化合成和2994最终resolve。场景保存并重新打开后UI组合仍然完整；未再次反复统计已确认的UI几何偏移。

native回放正常finally关闭，核对qrenderdoc进程数为0。本记录证明本轮关心的调度与持久化结果，不扩张为原FSR算法等价、动画稳定性或所有像素完全一致的声明。
