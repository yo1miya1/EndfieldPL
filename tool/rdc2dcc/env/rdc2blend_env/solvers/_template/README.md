# 解法包（solver pack）格式表

一个游戏 = `solvers/<名字>/` 一个文件夹：

```
solvers/mygame/
    solver.json     格式表：身份 + 所有常量
    solver.py       可选：只有表说不出来的东西才写代码
```

把它拷到 `solvers/` 下面，工具就会多出一个求解器，**不用改任何一行主流程代码**。
两个自带的求解器（`endfield`、`nishuihan`）就是普通的包，所以这套格式是被实际使用验证过的。

用法：

```powershell
rdc2blenderGUI.cmd run --capture X.rdc --solver mygame
```

GUI 的「基本」页「求解器」下拉框会自动列出来。

> `_template` 这个文件夹本身不会被当成求解器（下划线开头会被跳过）。

---

## solver.json 键表

### 身份

| 键 | 说明 |
|---|---|
| `schema` | 格式版本，现在是 `1` |
| `name` | 求解器的机器名（英文小写）。`--solver` 用的就是它 |
| `label` | 显示名，中文也行。GUI 下拉框里显示的就是它 |
| `description` | 一行说明它在哪里找调色板和相机，`doctor` 会打出来 |
| `notes` | 给人看的备注：这份表是在哪个捕获上拟合的、哪里还是猜的 |
| `base` | `solver.py` 不存在时用哪个内置基类：`Adapter`（默认，什么都不扫）或 `GenericAdapter`（永远走穷举扫描） |
| `adapter` | 和 `name` 一致即可；profile 里记录的求解器名 |

### 骨骼调色板在哪

调色板是一块结构化缓冲，里面每根骨头 3 个 float4（3 行 4 列的矩阵）。
基址由一个 u32 算出来：`基址(float4) = header_offset + 读到的 u32`。

| 键 | 说明 |
|---|---|
| `palette_base` | 候选列表，每项 `{cb, stride, index, component}` = 从哪读那个 u32。`cb` **可以写常量缓冲的块名**（如 `"PublicData"`），也可以写槽位号。`stride` 是每个实例记录占几个 float4，`index` 是记录内第几个 float4，`component` 是哪个分量 |
| `palette_header_offset` | 那个 u32 要加多少才是基址。**必须按 u32 位模式读**，按 float 读会得到垃圾 |
| `bone_stride_f4` | 每根骨头占几个 float4，正常是 3 |
| `palette_select` | 两块调色板（A/B）怎么选：`{cb, stride, index, component, less_than}`，值 `< less_than` 用 A，否则用 B |
| `skin_flag` | 判断"这个 drawcall 走蒙皮分支"的位标志：`{cb, stride, index, component, mask, clear_mask}`，`(v & mask) != 0 且 (v & clear_mask) != 0` |

### 相机在哪

| 键 | 说明 |
|---|---|
| `vp_rows` | 视图投影在哪个常量缓冲的哪几个 float4：`{cb, indices: [n,n+1,n+2,n+3]}`。`cb` 同样可以写块名 |
| `left_handed` | 进 Blender 时要不要镜像一个轴 |
| `up_axis` | 游戏世界的上方向：`"y"`（Unity 类）/ `"z"` / `"x"` |
| `unit_scale` | 1 游戏单位 = 多少 Blender 单位。厘米世界写 `0.01` |
| `flip_camera_y` | 恢复出来的视角相对游戏画面是不是上下翻的（见下） |
| `flip_y_before_eid` | 上下翻的**分界 eid**；一般留 `null`，跑的时候用 `--flip-y-before` 传 |

`model_rows` / `model_translation` / `origin_rebase` / `view_rows` / `fx` / `fy` / `near`
这几个键**目前没有被读**——物体矩阵是从拟合反推的（`Model = VP⁻¹·A`），
留着是为了兼容旧文件。

### 顶点数据怎么解

| 键 | 说明 |
|---|---|
| `normal_packing` | `"auto"` / `"xyz10"`（10:10:10:2 八面体）/ `"raw_float"` / `"none"` |
| `skin_weight` | 四根骨头权重怎么读：`"renormalize"`（四个都按比例缩到和为 1）或 `"remainder"`（保留前三个，第四个 = 1 − 前三个之和；着色器自己算第四根时用这个）。**选错会把每个顶点的权重悄悄减半** |
| `attribute_map` | 角色 → 属性名覆盖，例如 `{"NORMAL": "TEXCOORD3"}` |

### 导出什么、怎么摆

| 键 | 说明 |
|---|---|
| `scene.object_transforms` | 每个物体带自己的世界矩阵（默认 `true`） |
| `scene.fit` | Blender 原点放哪：`keep` / `character`（默认）/ `all` |
| `scene.matrix` | 直接给一个 4×4 顶掉推导出来的世界→场景矩阵 |
| `mesh_kinds` | 四类网格的开关与阈值，见主 README 的「导出什么网格」 |
| `select.min_bone_buffer_bytes` | 判定"绑了调色板"的缓冲大小门槛。**换游戏第一个要调的就是它** |
| `select.group_by` | 按什么分 render pass，默认 `["depth_target", "viewport"]` |
| `verify.accept_pose_rms` | 姿态残差验收门槛。厘米尺度世界要放宽（逆水寒是 `0.01`） |

### 找不到就扫描（兜底）

只有按上面找不到才会走到这里。`discover` 里的开关越全越慢：

| 键 | 说明 |
|---|---|
| `header_offsets` | 再试这几个 header 偏移 |
| `swap_palettes` | 把 A/B 候选顺序调过来再试一遍 |
| `scan_cbuffer_values` | 把记录里每个 u32 都当候选基址 |
| `scan_bone_stride` | 每根骨头占 3 个还是 4 个 float4，都试 |
| `scan_matrix_runs` | 在调色板缓冲里搜"连续的正交 3×4 块" |
| `max_align_delta` | post-VS 数组相对顶点缓冲的偏移搜索范围 |

---

## solver.py 能改什么

只要表能说清楚就别写代码。真要写时，覆写这几个钩子之一：

| 钩子 | 什么时候需要 |
|---|---|
| `vp_layout = "row_major"` | 着色器用 `dp4` 读那四个 float4（那它们就是行），而不是一列一个分量 |
| `camera_view(cbs, profile, meta)` | 相机块要**找**而不是直接读（引擎每次都换槽位），或者一个块里有好几个矩阵需要挑 |
| `keep_draw(draw, family, profile)` | 角色的 eid 区间里混了不属于它的几何 |
| `classify_attributes(inputs, profile)` | 某条流要按别的规则认（默认按名字编号 + 形状） |
| `decode_normal(raw, off, spec, packing)` | 法线打包格式不是内置那几种 |

`Adapter`、`GenericAdapter`、`position_declaration`、`infer_semantics`、
`skin_attributes`、`cb_slot`、`BUFFER_DESCRIPTORS` 已经在命名空间里，
**不要 import**（包名会随文件夹名变）。

---

## 上下翻（`flip_camera_y` / `flip_y_before_eid`）

Unity 类引擎**渲染到贴图**时会把投影矩阵的 Y 翻过来，**合成到后备缓冲**时不翻。
所以一帧里有一个 event id 是分界点，它换游戏换帧都不同，工具推不出来。

* `flip_camera_y: false` = 这个引擎不翻。
* 跑的时候用 `--flip-y-before <eid>` 给分界点，工具会按每个 draw 自己的 eid
  决定要不要翻（相机、深度参照、颜色目标都按这一条）。

**剪影 IoU 查不出这个错误**（相机和它对比的深度一起翻，`same` 照样 0.99）。
只能靠人眼：角色是不是头朝上。

---

## 验收一份新表

```powershell
rdc2blenderGUI.cmd run --capture X.rdc --solver mygame
```

| 看什么 | 期望 |
|---|---|
| `+ solved` 那一行 | 蒙皮网格的数量和你数出来的部件数一致 |
| `rms=…` | 蒙皮部件大多在 `1e-7` 量级；`>1e-3` 说明调色板或权重读错了 |
| `silhouette IoU` | `>0.95`；**并且 `same` 要比 `flipY` 高** |
| `renders/gamecam.png` | 角色**头朝上**、姿态和游戏一致 |
| `renders/game_vs_ours.png` | 我们的渲染和游戏自己的颜色目标并排，朝向一致 |

`python tests\selfcheck.py` 不需要捕获就能跑，改完先跑它。
