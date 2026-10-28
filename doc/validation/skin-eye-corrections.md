# 眼睛视差与皮肤分块修正

2026-10-28。参数仍来自SI-1原始CB；本轮不改灯光、曝光、视差强度或阴影bias。Shader读取当前Unity相机、Light和Renderer法线。

## 修前真实截图

主代理通过Unity编辑器Camera.Render抓取1024×1024无UI近景：

| 请求 | 位置/目标 | 证据 |
| --- | --- | --- |
| 203眼正面 | (.025,1.464,-.3) → (.025,1.464,-.06) | tmp/unity/captures/20261028-133715-540/editor-camera.png |
| 204眼侧面 | (.145,1.464,-.268) → (.025,1.464,-.06) | tmp/unity/captures/20261028-133716-126/editor-camera.png |
| 205/206/207颈部 | (-.30,1.45,-.18) → (-.03,1.41,-.01) | Final / Normal / Shadow，133716-664、133717-230、133717-758 |
| 208/209腿部 | (.22,.48,-1) → (.02,.45,-.15) | Final / Normal，133718-260、133718-799 |

眼正面可见从瞳孔中央向下延伸的UV裂缝，侧面同一部位仍有错位。颈部Final可见三角块；Normal大致连续，Shadow上半颈接近全黑，Final内部却仍有色块，因此不能只凭外观将问题归于shadow bias。

## 眼睛：插值切线长度被错误抹掉

证据是`doc/capture/shaders/1061_vs.txt`的198–205与PS37–61。源VS在顶点归一化N/T；PS不重新独立归一化T，而采用：

```hlsl
float inverseNormalLength = rsqrt(dot(N,N));
float3 tangentView = normalize(float3(
    dot(T * inverseNormalLength,V),
    dot(cross(N,T) * signW * inverseNormalLength,V),
    dot(N * inverseNormalLength,V)));
```

旧实现先`normalize(T)`、`normalize(N)`再构建B，确实与源式不同；数学上会抹掉插值切线缩短的信息。但对现502网格的中心三角形诊断（`eye-pole-tangents.json`）发现插值T长度最低约.989，没有接近零的极点退化。**该源公式修正不是本次裂缝已经证明的主要根因**；首轮213/214同角复拍裂缝仍在，不能据代码差异宣布修复完成。

修正集中在`Library/SourceEye.hlsl`。视差圆域、smooth权重、横纵缩放(1,.25)和`.1`原参数保持不变。PS80–95/452–460的虹膜/角膜法线也使用原始插值T/N及`cross(N,T)*tangent.w`，只在最终世界法线归一化。源43行是`lt(0,w)`，因此正手性符号保持正确，没有反号补偿。

另将间接基础色恢复为PS71–74的染色前纹理RGB；虹膜/眼白染色只进入对应直接材质响应，避免间接色重复乘染色。

| 对外字段 | 来源 | 本帧值/说明 |
| --- | --- | --- |
| `_EyeParallax` | 1061 PS slot6[12].y | .10000000149 |
| `_EyeCurvature` | slot6[17].y | 1.47200000286 |
| `_EyeIrisTint` | slot6[15].rgb | (.881132,.999201,1) |
| `_EyeScleraTint` | slot6[16].rgb | (2,2,2) |
| `_EyeReflectionColor/Strength` | slot6[18].rgb/w | 原值不变 |
| `_BaseMap_ST` | 502/1061 VS slot3[10] | 两者均(1,1,0,0)，UV变换一致 |

## 身体皮肤：半球输入错读了Ny

颈部/腿属于538 → 1019身体皮肤，不启用`EF_SOURCE_SKIN`的面部SDF变体，因此`_SkinHemisphereOriginOS`不是该部位的直接输入。

1019 PS93–96明确将扰动法线改排为`(Nx,2^-14,Nz)`后归一化；1053–1055才与G[116]做半球响应。旧实现却传入几何法线完整Ny。SI-1的G[116]≈(0,1,0)，G[117]=(.15,1.5,.5)，原水平法线的半球响应接近`.725`，旧实现则把网格Ny起伏放大到颜色响应中。

已在`EF_SOURCE_VIEW_TINT && !EF_SOURCE_SKIN`分支改为源水平扰动法线；面部SDF、实例原点、普通PBR和shadow bias保持各自原路径。这里没有用平滑法线或增亮补偿掩盖分块。

## 验证状态

已完成上述HLSL差异修正；首轮213–220复拍显示眼裂缝和腿部三角块仍存在，说明还有独立输入根因。不能把本轮模型修正当作实际问题已解决。

## 已证实的共同根因：发布N/T与实际源方向不符

定向补取502/1061、538/1019完整PostVS后，按现C# ReadMesh的真实链（placement inverse-transpose变换N、placement变换T、Blender→Unity B=(-x,z,y)）重现旧发布值，与源D3DWorld→Unity(-x,y,-z)比较，得到：

| 几何/实际Forward | 顶点数 | 法线角差中位数 | 切线角差中位数 | tangent.w不符 |
| --- | ---: | ---: | ---: | ---: |
| Eye502 / 1061 | 302 | 72.996° | 36.377° | 107/302 |
| Body538 / 1019 | 5553 | 92.067° | 27.796° | 2841/5553 |

完整结果见`skin-eye-import-directions.json`，源长度与正交性见`skin-eye-postvs-directions.json`。这不是浮点舍入或片元半球的小误差；它足以破坏眼睛视差方向、三角形间法线图基底以及受光响应。几何投影位置/UV已闭环，不代表N/T同步正确。

源502 GBuffer与1061 Forward的UV/N逐bit相同，502没有T输出（o4为motion），必须取1061 o3/o4。538与1019的UV/N/T逐bit相同。源方向长度误差在2e-7以内，正常顶点归一化不会破坏数据。Body源N/T却不是全部正交，max|N·T|=.434814，不能额外Gram-Schmidt“修正”源基底。

capture统一发布`Authoring/Extracted/SI1/CharacterDirections/{eid}/normal-tangent.float7`。每顶点7float为源D3DWorld N.xyz/T.xyzw；SceneBuilder在发布边界仅作(-x,y,-z)，不再次placement，保留真实w。运行时仍按Unity Renderer矩阵/当前相机与光照计算，不读取PostVS原件或捕获相机。实际N/T资产发布后必须再用相同近景复拍确认眼正面/侧面裂缝消失、颈腿色块改善；Shadow若仍有独立条纹继续单独定位。

## 实际修后结果

主代理223重新发布真实方向后，224–231按203–210相同相机参数复拍，独立目视确认：

- 224正面`20261028-135553-341`与225侧面`20261028-135554-664`的虹膜环连续，原从瞳孔向下的竖向/径向撕裂消失。
- 229腿部`20261028-135556-841`的原三角形明暗块消失，恢复连续受光。
- 226颈部`20261028-135555-179`主体受光已连续，衣料高光方向也更合理；颈下缘仍可见独立几何/阴影边界，不把它归入已修的N/T方向错误。

交付对比图`skin-eye-before-after.png`仅从203/224与208/229取相同矩形，保留原RGB像素直接拼接；无缩放、调色或alpha合成，裁切坐标与原文件记录在同名JSON。

232完整Game参考的同编码RGB比较在`comparison-232/`：2560×1440原生分辨率、full-frame MAE=5.559/255；Face ROI=19.019、Dress ROI=14.793。这个比较仍是中间差异证据，不等于全部材质最终验收。当前最高优先级是头发/额前与轮廓过黑：源635仅清RT0且G4逐byte保持，当前Lighting末尾额外OutlineColor硬写SceneColor=0需单独A/B证明等价；其次是衣料局部高光/暗部差异，应继续按源计算核对，不调颜色/粗糙度补偿。

240实际A/B关闭OutlineColor后头部过黑明显改善，证明该硬黑合成应移除。源655的509顶点/2304索引构成半径约25的包围球（统计见`source655-background-geometry.json`），因此其作者期材质发布为queue2500。正确顺序是GBuffer前景opaque≤2499→RT0-only SurfaceOutline→背景GBuffer2500；此阶段保留其它MRT并通过深度阻挡后画背景，无需SceneColor黑色补偿。该顺序由主代理通用管线实现，Shader数学不为此调宽度或颜色。

## 247最终整帧复核与单项材质差异

247真实Game图为`tmp/unity/captures/20261028-141049-863/editor-camera.png`，OutlineColor已删除、655已queue2500、UI保存已由重新开场景验证。`comparison-247/`采用同编码2560×1440 RGB、仅移除附带Alpha，全图MAE=5.529/255，Face ROI=17.435（232为19.019），Dress ROI=14.892，背景ROI约2–3.5。指标仍是差异定位，不代表全部材质逐像素相同。

此时最高优先级的材质差异仍是头发/额前偏暗。发现一处明确源式差异：1165 PS78将主法线图结果保存到r16，PS1121直接以r16与G[116]做半球响应；当前Hair分支错误地继承默认几何法线。已仅将`EF_HAIR`的半球输入改为`s.normalWS`，G[116]/G[117]、Ramp、光照、发丝瓣参数全部保持原值。需同247相机复拍验证，不能通过增加环境光/改变发丝颜色补偿。

259已按同247主相机复拍，路径`tmp/unity/captures/20261028-141603-272/editor-camera.png`。同编码RGB比较在`comparison-259/`，全图MAE=5.531/255，Face ROI=17.547、Dress ROI=14.927；与247的5.529、17.435、14.892基本持平，未出现可确认的整帧误差改善。不能把这次原式修正宣传成已消除头发残差，也不应为了略降MAE回退已确认的源式。

## 新机位侧胸/腋下：独立阴影三角台阶

前述229腿部与226颈部改善只覆盖对应机位，不能据此声称全身皮肤分块均已消除。用户新图的侧胸/腋下三角台阶在265 `20261028-143532-362`被精确复现。268 Normal、269 Shadow、270关闭全部Light.shadows均使用同一相机；`skin-side-shadow-isolation.png`从四张1200×900原图裁切相同矩形(380,180)–(850,620)，无缩放、调色或Alpha合成，出处见同名JSON。

本轮可见结论：268扰动法线连续，269阴影值准确复现长三角边界，270关闭Light.shadows后皮肤长三角台阶消失，腋窝的平滑底图纹理仍保留。因此本轮主要缺口属于接收/投射阴影路径，不能以重算法线、改变皮肤颜色或粗糙度修补。管线代理继续核对ShadowCaster与接收路径；位置/索引的源PostVS核验由capture代理独立完成。

针对Body538→1019的源公式和绑定重新核对结果：

| 项目 | 原证据 | 当前实现/实际值 |
| --- | --- | --- |
| UV和贴图 | 538 t0/t1，1019 t14/t15 | 同资源99604/99260；两份VS slot3[10]均(1,1,0,0) |
| 采样LOD bias | 两份PS slot1[26].x | 均-1.765534878，不另改MipBias |
| 法线强度/背面 | 538 M[0].w/M[1].y；1019 M[0].w/M[1].y | 均1/0；按R×A解码，Z在XY强度之前重建 |
| 片元基底 | 538 PS27–48，1019 PS27–38/56–65 | 保留插值N/T，B=cross(N,T)×w，重建后归一化；无额外Gram-Schmidt |
| 顶点方向 | 1019 VS230–237 | 源也分别单位化N/T；已发布实际PostVS方向单位长度误差<2e-7 |
| 视角染色 | 两份M[12].x/M[13].rgb | 均.3/(.637597,.376262,.296138)，与源相同的.85/.15曲线 |
| 半球 | 1019 PS93–96/1053–1055 | 当前用扰动N的水平投影(Nx,2^-14,Nz)；Body未启用Face的EF_SOURCE_SKIN或_SkinHemisphereOriginOS |
| 物理参数 | 1019 M[0].xyz | smoothness .258、specular .454、metal 0；已发布roughness .742，无本轮调参 |

本次没有发现可解释这些边界的新增Skin公式差异，因此未为此修改SourceCharacter的算法或材质值。阴影路径修复后仍需按265同机位复拍确认，不能将关闭阴影的诊断图当最终修复。

### 源Body确实接收主阴影，不能禁收规避

1019 PS1030从t4（ResourceId20410）按屏幕像素读取RG；其中G参与1051的`min(baseAlpha,screenShadow)`，1052再与Ramp.a取min，1056乘G[111].y（本帧=1）。1079和1100继续让该值参与材质响应/镜面组合。Body没有Face SDF路径，也没有本帧禁收selfshadow的材质开关证据。当前`EFMainShadow(positionWS)`内部仅做cascade选择、投影、原生depth compare/Tent，不读取法线或肤色；法线只参与Caster的normal bias位移。关闭阴影图仅用于定位，不能作为生产策略。

20410实际由903/914两段fullscreen producer写入。此前未提取这两份PS/CB，不能假定旧工程VisibilityCombine/DirectionalVisibility完全同源。旧VisibilityCombine约419–447行存在明确的receiver方法：由世界位置屏幕导数叉积取得真实三角面N，按`1-clamp(dot(faceN,L),0,.9)`缩放沿光线和面法线的偏移，再投影采样；不使用artist smoothN。旧DirectionalVisibility主cascade投影段则直接使用世界位置。已向capture请求仅补903/914与BodyShadow372，以确认SI1实际生效分支及语义值；确认前不搬入未匹配偏移、不增大bias、不改变Body接收策略。

### 903/914/372定向提取后的确认与实现

实际证据已存入`Authoring/Extracted/SI1/ShadowReceiverNative`。本帧903的G输出恒1；914的cb3[35].w=1，跳过普通主cascade。角色G来自独立角色阴影图t2，经GB2 one-hot actor位选择投影。**914用GB3读取后解码的扰动法线，不是903/旧Combine的屏幕导数面法线。**因此不能把上段候选面法线偏移直接套到角色。

914 cb3[128..131]是角色0投影；其UV-X世界梯度长度=.594851673，cb3[218].zw×[233].zw得到1024×1024 tile。`1/(gradientX*tileWidth)=.00164169069`，与cb3[188].z相对误差2.32e-8，证实它是X方向worldTexel；Y方向为.00190851，不能取max/平均代替。cb3[188].xy恰为3/6个X worldTexel。运行时从Unity当帧角色阴影矩阵和图集尺寸重算worldTexel，不使用固定世界毫米数。

源接收点为`P'=P-outwardLight*(3*worldTexelX*f)+perturbedN*(6*worldTexelX*f)`，`f=1-clamp(dot(perturbedN,outwardLight),0,.9)`。cb3[203]=(.303235859,-.422618300,-.854073882)，与source towardLight=(-.303235918,.422618270,.854073644)反向，误差≤2.38e-7；投影depth梯度(-.119924814,.167138621,.337772220)归一化后与towardLight同向。因此减去row203是向灯光移动并增大reversed-Z深度，不是任意反号。完整数值及关系见`character-shadow-receiver.json`。

源核16次Gather读取64个深度，UV半径为`4/atlasWidth`这一标量同时用于XY，屏幕像素模4决定旋转。令`b=count/32-1`、`e=1-abs(b)`、`d=saturate(sumPositiveDepthDelta/(count*receiverDepth))`，可见性为`.5-.5*sign(b)*(1-lerp(e³,e,d))`；它不是普通PCF均值。16组常量从真实914 DXBC immediate buffer逐位提取，见`character-shadow-kernel.json`。`CharacterShadows.hlsl`已保留原核和中文注释，并接入SourceCharacter主阴影入口。

动态契约为每角色组MPB `_CharacterShadowIndex`、16组实时投影/矩形/方向/偏移和原生深度图。GB2仍为10/10/10/2载体；保留非actor位，动态actor占8..23 one-hot，角色0仍为原258。未注册对象清除捕获actor位并回退普通Unity主光阴影，避免调试与Forward采错组。独立角色图、无vertex bias的专用Caster及Post Shadow调试由pipeline代理接入；source372的Native raster bias为-8/0，对应Unity逻辑8/0。语义Profile由生成器从真实CB/状态导出并写入scene-import，运行资产不引用原始CB。

此处记录的是已证实的原机制缺项和落盘实现；仍需265同机位Final/Shadow复拍，确认独立阴影链实际生成并消除剩余台阶，不提前宣称视觉修复完成。

### 281同机位实际复拍

281 Final为`tmp/unity/captures/20261028-152231-124/editor-camera.png`，Shadow为`20261028-152231-289/editor-camera.png`。独立目视确认：265侧胸上方的长斜向三角台阶和腋下/胸侧下半部的大块三角分段均已消失，背光区连续；衣物边缘的投影仍存在，未关闭接收或把shadow固定为1。

`skin-side-shadow-before-after.png`由265与281 Final裁切相同矩形(300,80)–(900,780)并排，保留原RGB像素，无缩放、调色或Alpha混合。仅额外留24px文字标记边；原图路径/尺寸/SHA256及裁切记录见同名JSON。281 Shadow中相同区域也不再出现原长三角阶梯，支持本轮是实际角色阴影路径修复，而非单独改变肤色或法线掩盖。

仍有明确限制：极近距离的软影过渡可见源16Gather核的4×4屏幕旋转采样纹理。原常量与过滤数学已保留，未添加无来源的blur或修改3/6偏移掩盖纹理。当前结论限定为该复现机位的侧胸/腋下割裂已消除；不据此宣称所有相机/材质逐像素一致。Shader已冻结供主代理整帧RDC与构建验证。

`comparison-259/head-source-247-259-rgb.png`提供源图/247/259相同头部裁切，保留原RGB、不缩放。剩余差异主要仍是发丝明暗/轮廓与衣料局部镜面、阴影/时间重建的综合差异；当前ROI同时包含面部与遮挡边缘，不是可用于反调某个材质颜色或粗糙度的隔离指标。眼裂缝与颈腿分块的实际修复结论保持有效；材质逐像素一致性没有据此宣称完成。259后Assets冻结供主代理batchbuild，未继续试调任何参数。
