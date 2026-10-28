# 当前进度

更新：2026-10-28；阶段：用户确认UI正确、其他功能无大问题，本轮收尾完成。

- 已建立 Unity 6000.6.3f1 工程、自定义七阶段SRP、五张GBuffer及每相机资源管理。实时Camera、Light、Unity阴影剔除和Volume已接入。
- SI-1角色流程已提取，22个角色/环境/特效部分已生成普通Mesh、Material、Texture和Prefab；95个UI绘制已转独立网格和7类语义材质。
- 原图、源常量、生成工具与运行内容已分离。运行时不解释源CBuffer或读取RDC/JSON；材质映射已发布到Authoring，重建不依赖tmp。
- 已通过实际编辑器运行，并取得Game/Scene截图及完整Unity RDC。坐标、阴影投影对象、环境光持久化、UI方向、线性颜色重复解码、原生ReflectionProbe绑定均已定位并修复。当前继续收敛角色局部着色、Ink采样与时序抗锯齿；编译与截图成功不代表最终效果验收。
- 59张材质纹理以GPU解码线性Half和完整源mip发布，静态环境Cube通过Unity ReflectionProbe提供。语义颜色在导入边界适配Unity Color Inspector，运行时不重复解码。
- SceneView和Game共用后处理，UI只在Game；调试GBuffer视图跳过UI覆盖。
- 2026-10-27发生一次RenderDoc截帧期间的驱动线程崩溃，已恢复工程，记录见 `../validation/editor-crash.md`。
- 后续截帧器已在GPU回读完成后结束捕获；086记录195个draw、317个动作。该帧探针采样明确为原生Cubemap，证据见 `../validation/reflection-binding.json`。

设计约定见 `../architecture/project-contract.md`，未决事项见 `../decisions/open-questions.md`。

## 本轮完成与当前问题

- 眼睛视差接缝、颈腿的三角形明暗：修正源姿势法线/切线发布与对应源公式后，224–231同机位复拍确认改善，见`../validation/skin-eye-corrections.md`。这不代表所有角度的皮肤问题都已解决。
- 头发轮廓：前景GBuffer后只写RT0，再绘制背景GBuffer；保留其余附件和bit16面部/眼睛保护。错误的Lighting尾部黑色合成已删除。247完整GPU截帧确认实际调度，见`../validation/unity247-final-order.md`。
- 台面动态阴影：接入实际世界位置的主灯阴影，并按Unity主灯与环境光的能量比例衰减，环境光不随遮挡归零。
- 多光源：两份独立展示场景已保存；方向光、点光、聚光的开关对比和完整GPU截帧已完成，附加阴影图集覆盖六面点光、聚光及方向光，见`../rendering/multi-light-demo.md`。
- 最新Windows Player已包含头发原式修正、角色独立阴影与Game视口UI方向修复。295在实际编辑器中调用BuildPlayer成功，构建结果Succeeded、errors=0、总内容797558723字节；回执`tmp/unity/commands/295-build-ui-final.result.json`，报告`tmp/unity/player-build.txt`，程序`tmp/build/Windows/EndfieldRebuild.exe`。此前独立批处理构建也以退出码0完成；旧091未完成，不作为成功依据。
- 最新侧胸/腋下机位：Body538的5553顶点、27468索引与源匹配，问题来自遗漏的角色局部阴影路径。补取914/372后重建D16角色图、源3/6纹素接收偏移及64深度过滤；281同265机位确认三角台阶消失，正常遮挡保留。没有重算法线、修改拓扑或调肤色。近距软影仍可见源4×4旋转采样纹理，见`../rendering/character-shadows.md`与`../validation/skin-side-shadow-before-after.png`。
- 282完整Game图及RDC已生成，283 Scene图已生成。相同RGB编码比较中，全图MAE从261的5.532降至5.055/255，Face ROI从17.514降至14.442，Dress从14.935降至13.395。仍有头发/衣料和时序重建残差，不能把这个指标称为逐像素复刻完成。
- 282实际GPU验证确认独立D16图、1024有效viewport、9个position-only/CullOff投影draw，以及角色接收端绑定同一图集和3/6纹素参数。投影与接收矩阵验证误差低于2e-7，UI保留95+2次绘制。284保留地面投影；286已打开保存后的角色多光源场景复拍。见`../validation/unity282-character-shadow.md`。
- 用户随后指出真实Game视口UI倒置：已修复内部Composition提前应用backbuffer方向的错误，用户提供实际编辑器截图确认修复。此前离屏图仅证明RenderTexture路径，不能代替该验收；见`../validation/ui-game-view-orientation.md`。

## 收尾

用户已确认“测试其他功能也没有大问题，可以收尾了”。当前代码、发布资产、SI1场景与Prefab均已保存，Unity编辑器保留SI1场景，最新Windows构建位于上述tmp目录。验证图片与参数映射保存在doc，未解决的近距阴影采样纹理、局部材质及时间重建差异保留记录，不影响本轮已确认问题的修复结论。
