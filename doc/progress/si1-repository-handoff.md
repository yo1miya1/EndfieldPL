# SI1 管线仓库快照交接

整理时间：2026-10-29（Asia/Shanghai）。来源工作区为 `F:/Project/_Game/EndfieldRebuild`；目标真正 Git 根为 `F:/Project/_Game/Endfield/EndfieldPL/EndfieldPL`，Unity Hub 打开其 `pro/`。外层 `F:/Project/_Game/Endfield/EndfieldPL` 本身不是 Git 根，既有外层 doc/tmp 未改。

这是详细工具手册完成后的现有 SI-1 快照。**没有 Typhon2 内容或迁移改动**；后续 Typhon2 仅在原 EndfieldRebuild/pro 另行处理。本次没有启动 Unity、重新导入/发布、跑项目测试或重做截图，历史验收结论保持来源说明。

## 保留内容

- `pro/Assets` 完整复制，包含全部 `.meta`：通用 SRP/Shader/材质 Inspector、SI1 角色与环境的完整 Mesh/Material/Half mip贴图/Cubemap/Prefab、场景相机UIComposition、独立角色阴影组件、Settings 与两张 MultiLight Demo 场景。
- `pro/Packages` 的 manifest 与 lock、`pro/ProjectSettings`：编辑器6000.6.3f1，Core17.6.0等依赖与源工程设置。
- `doc` 的学习、实现、来源与实际验收记录；根 README；`pro/Authoring/README.md`、`Tools` 离线脚本与配置模板。
- `pro/Assets/Authoring/Editor` 发布/桥接/截图/诊断代码，位于完整 Assets 复制范围；`tool/rdc2dcc` 本地外部工具副本和实际改动，排除 Python cache。
- 既有目标 `.git`、branch/main、origin、初始 HEAD 与 `.gitattributes` 原规则保留。仅追加精准 Content/Textures 与 Meshes `.asset` 的 LFS 属性，并新增常规 Unity `.gitignore`。

复制采用添加式 robocopy `/E /COPY:DAT /DCOPY:DAT /XJ`，没有 `/MIR`、删除、reset、clean、移动源目录或覆盖 Git 元数据。复制开始时目标工作区干净、业务目录尚不存在。README与操作手册仅在目标副本补充仓库位置/输入边界，原工作区未改。

## 排除内容

未复制 `pro/Library`、Temp、Obj、Logs、UserSettings、空历史 pro/Endfield；未复制根 src/tmp（含RDC、桥接命令、过程PNG、replay、日志和Player构建）；未复制 `pro/Authoring/Extracted`、Work、RetiredPublished；未复制 pycache/pyc/pyo。完整文档内已经整理保留的证据图片/JSON仍属于doc。

## 运行与再生成的边界

Unity Hub 打开 `pro/`，然后打开 `Assets/Endfield/Scenes/SI1.unity`，可使用保存的 SI1、UI、环境与动态Unity灯光/阴影/后处理。多光源示例为 `MultiLightDemo.unity` 与 `MultiLightCharacterDemo.unity`。运行材质使用已发布 Unity 资产，不要求原始RDC、Extracted或外部工具。

重新发布不是开场景的必要步骤。再生成需要将源工作区 `F:/Project/_Game/EndfieldRebuild/pro/Authoring/Extracted/SI1` 的完整输入恢复到本仓库 `pro/Authoring/Extracted/SI1`；从RDC重采集另恢复 `src/SI-1.rdc` 并按手册配置工具环境。当前保留的 Authoring 菜单在缺输入时无法完整执行，不能解释为无输入一键转换。工具和原数据可删除而不影响已发布场景；删除后也不再具备再生成能力。

手册 `$EndfieldRoot` 指向当前真正仓库根，`$ProjectPath` 为该根下 pro。桥接未来输出该根下 tmp/unity，构建未来输出 tmp/build；此次未复制或生成这些结果。源构建产物的历史文件名仍为 EndfieldRebuild.exe，未因仓库改名擅改运行产品配置。

## Git 与复制核对

发布像素/网格 `.asset` 由路径规则使用 Git LFS；场景、Prefab、材质、Volume配置、代码、文档和 `.meta` 正常Git。未执行 git add、commit、push、LFS历史迁移或全局配置修改；当前文件为工作区新增/修改，交用户审阅。已有 HEAD 仍为 `843bc49c56a133aa50bc3f2451f5bf7a12c8aab4`。

复制仅进行文件数量、相对路径、长度与robocopy退出码核对，不重跑项目测试。核对结果：

|范围|源文件数|目标文件数|结果|
|---|---:|---:|---|
|pro/Assets|826|826|全部相对路径存在、长度一致|
|pro/Packages|2|2|全部相对路径存在、长度一致|
|pro/ProjectSettings|24|24|全部相对路径存在、长度一致|
|doc|309|310|无缺失；仅操作手册按目标根改写，另增本文|
|pro/Authoring/Tools|38|38|全部相对路径存在、长度一致|
|tool/rdc2dcc（排除cache）|35|35|全部相对路径存在、长度一致|

六项 robocopy 退出码均为1（正常复制新增文件），复制进程最终退出码0。根README和AuthoringREADME另行复制后仅在目标作边界说明。上述排除目录全部不存在于目标，工具Python缓存数量为0。Git状态仅既有.gitattributes修改及新增.gitignore/README/doc/pro/tool，暂存区为空，HEAD未变；`git check-attr`确认Content纹理/网格匹配lfs、SI1场景不匹配lfs。
