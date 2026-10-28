# 资产发布与可删除边界

## 三类内容

1. `pro/Authoring/Extracted/SI1` 是离线输入。`Source` 保存 rdc2dcc 角色流程的模型、完整顶点流、源程序和 CBuffer 证据；`Textures` 保存原图。这些文件供解释和再次生成使用，不参与游戏渲染。
2. `pro/Authoring/Tools` 和 `pro/Assets/Authoring/Editor` 是生成工具。前者合并已明确的几何、材质和场景参数映射；后者创建普通 Unity 资产、保存场景与构建。它们不会被编入玩家程序。
3. `pro/Assets/Endfield` 是可保留的效果内容。Mesh包含捕获姿态几何与UV/法线/切线；Texture资产保存独立像素；Material保存语义参数和纹理引用；Prefab和Scene引用这些发布资产；Runtime及Shaders实现当前实时渲染。

## 发布过程

`rdc2dcc --origin character` 得到统一角色原点。导入器按每个部分的 `placed` 标志处理变换，全部几何和相机统一减去角色原点，再在单一边界转为Unity坐标。它不恢复连续骨骼动画，也不把后处理图当模型贴图。

材质的输入记录保留来源EID、资源ID及CBuffer槽位，运行时只保留有意义的材质值。光源在生成场景时创建为真正的 Unity Light；之后每帧由剔除结果读取，修改Light或Camera即可影响画面。

静态纹理通过生成器发布为独立的Texture `.asset`。59张材质输入优先使用 `TexturesNative` 中GPU解码后的线性RGBAHalf及完整源mip链，不再根据原SRV的sRGB标记重复解码。原生数据保留D3D行序；兼容PNG输入仅在导入边界还原行序。PNG本身也是线性采样值，早期误按sRGB导入造成的偏暗已通过实际GPU值定位。运行材质不再引用PNG、Half原始文件或Source JSON。

语义JSON中的颜色是源GPU线性值；发布为ShaderLab Color时先转换为Unity Inspector使用的显示颜色，上传后恢复原线性值。Vector系数不转换。当前保真版保留未压缩Half纹理（59份来源数据约561MiB），以避免重新有损压缩和线性8位量化；它不是面向移动端的资源压缩预设。

静态环境Cube保留源预滤波的全部8级mip，导入时统一世界基底，发布成Unity Cubemap资产并赋给真实ReflectionProbe。它是环境辐射输入；Shader仍用当前Unity法线、视线和探针绑定求反射，不把源屏幕、阴影或深度作为运行贴图。

## 如何清理

关闭Unity后，可独立删除以下目录及其相邻 `.meta`（如存在）：

- `pro/Authoring/`：所有导出源资产与离线脚本。
- `pro/Assets/Authoring/`：编辑器生成/诊断菜单。
- `tool/`：外部工具副本。
- `src/`：原RDC；删除意味着不能再从此输入重提。
- `tmp/`：过程文件；需要的最终证据应先保留到 `doc/`。

保留 `pro/Assets/Endfield`、`pro/Packages`、`pro/ProjectSettings` 即保留工程所需内容。Unity自身的 `Library` 可随时由编辑器重新生成。

`Assets/Endfield/Editor`是可保留的材质Inspector与Pass设置，不是生成工具；它不读取Authoring资料。保留该目录可继续按家族编辑材质。

2026-10-28最新发布已取得保存场景的Scene/Game图像、包含角色独立阴影的完整GPU截帧和成功的Windows Player构建。运行组件与Shader均在Endfield目录；生成器和诊断入口均在Authoring目录。没有通过反复删除源目录做预防性测试；未消除的画面差异仍记录在进度和验证文档中。
