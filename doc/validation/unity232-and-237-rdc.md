# 232角色帧与237多光帧的实际GPU状态

只读取主代理实际Unity编辑器截帧，不启动Unity、不发送bridge命令。本轮未重新调查源SI-1。两份RDC均先创建独立ASCII工作副本并核对SHA-256，记录在tmp/capture/Unity232-integrity.json与Unity237-integrity.json。

## 232角色帧

原始路径：tmp/unity/captures/20261028-135558-535/editor_capture.rdc。SHA-256为4784d3080a7eb1cffbe12db7c624ed81b449164117b98eb0d6664916b85fbfe0。实际326个actions、185个draw。

- Outline为EID570，实际只绑定RT0=54417与depth=54437，其余MRT为空。CullFront时有效背面Stencil为Equal、ReadMask16、Ref0、WriteMask0；Face352和Eyes505的有效正面写入Ref16/WriteMask16。GPU附件与保护位规则已接通，不能再称这张帧仍在全五MRT描边。
- TAA resolve为1535，实际读取current54413、history53500、motion54449、opaque depth54443。CB末行(1,.1,.9,0)对应HistoryValid=1、currentWeight=.1、varianceScale=.9；持久history为RGBAHalf，全部finite、最大22.578125、非零约99.97%。
- motion为RGHalf，全图finite且为0。前面确有camera motion全屏1323以及对象motion1363等真实绘制；这是静止相机/静止模型帧，不能据零motion称运动pass失效，也不能以此单帧验证运动拖影和遮挡显露。
- main shadow为2048²深度53534，实际接收CB参数(1,4,1/2048,50)，深度全finite，非零约0.764%。它被地面1025等实际绑定；地面缺影并非atlas没生成。

地面1025的实际PostVS法线全部NaN。已核源Background/world2四个normal原本全零：source1210是unlit，所以早期导出不消费该字段。现在实时shadow ratio需要真实N，normalize(0)使NdotL/SH失效。prepare_background.py已按真实三角形面积加权恢复朝上法线，Unity方向约(7.9e-7,1,9.97e-5)，需主代理重新发布Mesh才会生效。不能用调shadow tint绕过错误法线。

buffer统计在unity232-buffer-statistics.json，原native状态在tmp/capture/unity232-details。

## 237四灯学习场景

原始路径：tmp/unity/captures/20261028-135957-938/editor_capture.rdc。完整实际状态、CB值、atlas tile覆盖与哈希在unity237-shadow-summary.json。

Lighting EID447实际绑定main深度56802、additional深度56806：D32_FLOAT写入视图，R32_FLOAT采样SRV，两个atlas均2048²。AdditionalLightCount的GPU整数值为3，加上main共有4灯。追加阴影参数按Unity可见灯顺序分别为：填充方向光(1,1,start0,type0)、spot(1,1,start1,type0)、point(1,1,start2,type1)。因此8个有效slice是1个方向光+1个spot+6个point cubeface；不能凭创作时的灯对象顺序猜runtime索引。

八份matrix均finite，八个rect覆盖4列×2行512² tile，并带半texel内缩。实际shadow draw使用additional深度56806；point部分面没有caster而未提交DrawRendererList，这是正常视锥剔除，空tile不表示缺少6面矩阵。additional atlas全finite、非零约4.888%。

实际caster VS的point type=1、normalBias=0；spot type=1并使用位置(2.5,3.5,-2)，说明punctual路径没有继续沿方向光常量做偏移。方向光使用type0。

实际比较sampler为Linear comparison、Greater。main和三盏额外灯的soft flag均为1。编译PS反汇编有20条sample_c，来自main hard1/soft9与additional hard1/soft9的备选分支；每盏有效软阴影路径是5×5 Tent的9次双线性比较，不能把20解释为每灯执行20 taps。反汇编在unity237-pixel.asm。

上述证明atlas、slice元数据、shader绑定与软硬分支已接通。主代理另外做的all/on与off可见阴影差异是图像证据；本记录不把单帧静态状态当成动态所有灯型的长期稳定性验证。所有native回放均执行finally关闭，核对后无qrenderdoc进程遗留。后续最终Game帧只需检查新Outline与背景顺序，避免重复整套源采集。
