# 282独立角色阴影GPU补验

读取实际Game截帧tmp/unity/captures/20261028-152440-599/editor_capture.rdc；先创建独立ASCII副本并核对SHA-256。一次回放只选新增角色阴影、身体GBuffer/receiver与UI存在性，没有重复CSM、额外灯或TAA审计。完整哈希、矩阵和状态在[unity282-character-shadow.json](unity282-character-shadow.json)。

## 独立图集与caster

角色图集为Resource28104，2072×1036的R16_TYPELESS资源，写入视图D16_UNORM、接收采样视图R16_UNORM。包含guard的布局与有效1024² tile分开：实际viewport为(6,6,1024,1024)。原始D16数据非零约8.345%，最大54990/65535，图集确有实际深度。

九个caster事件178/184/188/191/195/199/202/205/211均写同一28104，CullOff、native DepthBias=-8、SlopeScaledDepthBias=-0.0。九份VS bytecode hash完全相同。实际编译VS输入只有POSITION和UV，执行ObjectToWorld→当前shadow VP→near clip；没有NORMAL/TANGENT输入或normal displacement。不是仅把normalBias参数设0后仍计算0×NaN。

## 实际receiver、当前矩阵与3/6参数

身体receiver为530，实际t2绑定同一28104的R16_UNORM SRV。编译PS含16条指向t2的Gather指令，读取64个原始深度；没有把角色接收器替换成普通比较sampler的PCF。

GPU参数为(1,.0015915996627882123,3,6)，过滤半径4，角色组数1，当前towardLight=(.30323595,.42261827,-.85407364)。有效rect约(.00289575,.00579151,.49710426,.9942085)，与guard/viewport对应。

从GPU WorldToShadow矩阵的X世界梯度与实际atlas宽2072反算worldTexelX=.0015915996215749844，与上传值差约4.1e-11。矩阵深度梯度归一化也与当前light方向一致。它不是把源绝对世界矩阵和固定.00164169世界数值写进运行参数。

进一步用5553个身体真实caster PostVS验证：将其SV clip换成D3D顶行UV并应用guard rect后，与实际receiver矩阵投影匹配，最大误差XYZ分别约(4.07e-8,1.81e-7,1.14e-7)。这闭合当前caster geometry、光照投影/包围体拟合和接收矩阵；此单帧仍不代表已做移动角色/移动灯光的长期稳定性测试。

## actor0与GB2、UI

身体GBuffer为292，实际UnityPerMaterial的_CharacterShadowIndex（row9.x）为0，区别于材质默认-1；receiver对应groupCount=1。GB2精确uint payload258有617546像素，对应原低位2＋actor0的bit8。原源载体本来也是258，因此不能只凭258宣称MPB接通；实际上传index0、组数1和实时receiver绑定共同构成证据。背景其它载体不应误解释成有效actor0。

UI仍为97次draw：95个源网格加2次合成。回放成功关闭，随后qrenderdoc进程数0。此文档只确认新链路实际GPU绑定与状态，最终阴影外观由主代理PNG与后续图像对比评价。
