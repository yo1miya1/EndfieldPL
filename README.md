# EndfieldPL

保留完整 SI-1 角色、环境、UI 与多光源示例的 Unity 6 自定义渲染管线学习工程。Unity Hub 打开本仓库的 **`pro/`**，本机整理后的路径为 `F:/Project/_Game/Endfield/EndfieldPL/EndfieldPL/pro`；编辑器版本 **6000.6.3f1**，场景位于 `Assets/Endfield/Scenes/SI1.unity`。运行已保存场景不需要原 RDC 或离线提取目录。

本仓库是 `F:/Project/_Game/EndfieldRebuild` 在 2026-10-29 整理的 SI-1 快照，**不包含 Typhon2 迁移**。未拷贝原始 `src/SI-1.rdc`、`pro/Authoring/Extracted`、Work、旧发布归档、Library、日志、临时截帧或 Player 构建；输入仍保留在源工作区的 `F:/Project/_Game/EndfieldRebuild/pro/Authoring/Extracted/SI1`。需要重新生成时，先把完整输入恢复到本仓库的 `pro/Authoring/Extracted/SI1`；需要从 RDC 重采集时另恢复 `src/SI-1.rdc`，再按手册设置当前仓库根路径。保留的生成器菜单不表示离线输入已随 Git 提供。

发布的 Mesh/Texture `.asset` 采用精准 Git LFS 规则，未来克隆含这些受控资产的版本需安装 Git LFS 并下载对象；`.meta`、场景、材质和配置仍保留正常 Git 文本。此次整理未暂存、提交或推送。范围与复制核对见[SI1 仓库交接](doc/progress/si1-repository-handoff.md)。

2026-10-28已修复眼睛视差接缝、颈腿分块着色、头发轮廓和台面投影，并完成独立多光源场景的截图与GPU截帧验证。最新侧胸三角台阶已通过独立角色阴影路径修复，网格位置和索引未改。头发/衣料局部、近距阴影采样纹理和原时序升采样仍有残差，当前状态不是逐像素完全复刻。

Game视口UI方向已修复，用户确认实际编辑器效果及其他功能无大问题，本轮已收尾。源工作区的最新Windows构建已通过；历史输出为`tmp/build/Windows/EndfieldRebuild.exe`，本仓库没有复制构建产物，也没有为整理快照重新运行测试。具体记录见[进度](doc/progress/status.md)。

## 需要保留什么

| 内容 | 位置 | 是否为显示场景必需 |
| --- | --- | --- |
| 场景、Prefab、Mesh、发布贴图、材质 | `pro/Assets/Endfield/Content`、`Scenes` | 是 |
| 通用管线、Shader、Volume配置 | `pro/Assets/Endfield/Runtime`、`Shaders`、`Settings` | 是 |
| Unity依赖和工程设置 | `pro/Packages`、`pro/ProjectSettings` | 是 |
| 材质Inspector与材质状态设置 | `pro/Assets/Endfield/Editor` | 编辑学习时保留；不依赖提取工具 |
| 原始截帧 | `src/` | 否，重新提取时使用 |
| 截帧导出的FBX、顶点流、原图、反汇编、常量 | `pro/Authoring/Extracted/` | 否，重新生成时使用 |
| 离线生成脚本 | `pro/Authoring/Tools/` | 否 |
| Unity编辑器生成与诊断工具 | `pro/Assets/Authoring/` | 否 |
| 修改后的外部工具副本 | `tool/` | 否 |
| 日志、过程截图、构建和回放中间产物 | `tmp/` | 否 |

运行材质只引用发布的 Unity 贴图资产，不指向原图目录。删除 `pro/Authoring/`、`pro/Assets/Authoring/`、`tool/` 和 `src/` 不应破坏已保存的效果场景；源资料删除前可自行归档，以便未来换角色。

## 学习入口

- [从 RDC 到 Unity 的工具与详细操作手册](doc/learning/rdc-to-unity-tool-workflow.md)：工具实际改动、采集命令、数据整理、Unity 发布、换角色与自动化边界。
- [从场景到最终画面](doc/learning/rendering-walkthrough.md)：打开场景、修改灯光与材质、理解阶段边界。
- [管线结构](doc/rendering/pipeline-design.md)：从相机剔除到七个渲染阶段。
- [参数和着色模型](doc/rendering/shading-models.md)：源公式、语义参数与当前限制。
- [资产发布边界](doc/architecture/asset-publication.md)：原始资料如何变成独立场景。
- [本轮眼睛/皮肤修复](doc/validation/skin-eye-corrections.md)、[修前后图片](doc/validation/skin-eye-before-after.png)。
- [多光源演示与验收](doc/rendering/multi-light-demo.md)：`MultiLightDemo.unity`和`MultiLightCharacterDemo.unity`直接打开即可查看，灯光是可编辑的Unity组件。
- [角色局部阴影](doc/rendering/character-shadows.md)：与场景级联阴影分开的动态投影、接收偏移与源参数解释；[侧胸修前后](doc/validation/skin-side-shadow-before-after.png)。
- [实施取舍](doc/decisions/open-questions.md)、[进度](doc/progress/status.md)。

Scene 和 Game 共用光照、阴影及后处理，Game 额外绘制 UI。所有编辑器自动化使用 Unity API 和 RenderDoc API，无 Computer Use。
