# 已pose网格的真实法线/切线修正

这次修正的是离线模型方向数据，不是在运行shader中固定相机法线。Mesh位置、UV、三角形和当前Unity对象/相机矩阵仍然参与正常渲染。原先文件包含normal/tangent字段，并不自动证明其方向与本帧实际VS一致。

## 同一导入链的数值核对

旧方向按SceneBuilder.ReadMesh的完整链计算：placed时使用scene placement；normal乘placement逆转置，tangent乘placement，随后B(-x,z,y)，tangent.w乘placement行列式符号。源真实PostVS世界方向则经过C(-x,y,-z)。两者都按导入器归一化后比较，排除仅是不同坐标空间造成的假差异。

| 几何 | 旧N逐分量平均绝对差 | 旧T逐分量平均绝对差 | tangent.w不同顶点 |
|---|---:|---:|---:|
| 488 FaceDetail | 0.000024 | 0（保留） | 0 |
| 502 Eyes | 0.621581 | 0.317883 | 107 / 302 |
| 520 ClothingA | 0.755055 | 0.303267 | 390 |
| 538 BodySkin | 0.688282 | 0.267237 | 2841 / 5553 |
| 553 FaceSkinDetail | 0 | 0 | 0 |
| 568 FaceSkin | 0.562180 | 0.326781 | 716 |
| 585 ClothingB | 0.632838 | 0.283932 | 11933 |
| 599 ClothingC | 0.644518 | 0.293881 | 2132 |
| 617 Hair | 0.666335 | 0.319792 | 7754 / 17162 |
| 655 Environment | 0.000034 | 0.000078 | 0 |

完整最大误差、向量长度、N·T和每个draw数据在doc/capture/character-directions-validation.json。对Hair即使拟合任意固定3×3矩阵，旧N对实际N平均误差仍约0.403，不能以单个全局旋转或统一翻符号修复。553此前已由完整PostVS恢复，恰好零误差，进一步支持这次坐标链比较方法。旧packed方向的导出/解码尤其可疑；本记录不把未经逐指令追查的decoder推断写成已证明根因。

## 新方向文件与配对

CharacterDirections/import.json为稳定清单；每个子目录normal-tangent.float7按原world2顶点顺序存小端float32 Nx,Ny,Nz,Tx,Ty,Tz,Tw，源空间为D3D world，已经包含本帧pose。主发布器转换(-x,y,-z)，不再乘placement；随后仍通过Unity当前模型矩阵进入世界与相机空间。

每个文件均验证vertexCount与UV0全部float32逐值相同。502的GBuffer VS没有T输出，o4为motion，不能把它误当切线；这里采用1061 Forward实际o3 N/o4 T，与502 UV和N逐bit相同。538采用本身o3/o4，与1019 Forward的UV和N逐bit相同。655的normal/tangent寄存器是o2/o3，不能套角色o3/o4。1190是无光照环境effect，VS没有几何N/T输出，明确排除。

488源VS只输出N，当前FaceDetail材质不消费T；该子件只修实际N，T保留原导入方向，在每份import.json中明确标注，未冒称实际PostVS切线。

新文件中的实际N/T与各自原始PostVS的float32数据逐值相同。应用规定的C变换后，离线数值闭环误差为0；这是文件/导入数学的验证，尚不代表当前Renderer GPU已经更新或最终着色完全一致，仍须统一发布后的Unity截图/RDC确认。

## 不要强制修成另一套切线基

Eye1061的N/T均为单位，max|N·T|约1.34e-7。Body1019的N/T也分别单位，但max|N·T|约0.434814：源数据本身并不处处正交。这里保留实际方向，不做Gram-Schmidt、不擅自反tangent.w；源片元程序如何插值、归一化和构造副切线由对应材质公式决定。

此次源回放只补11个基础draw的状态/方向及1061/1019必要Forward数据，未重做全帧调查。native exporter均在finally关闭controller/capture，随后无qrenderdoc进程遗留。后续对最终Unity RDC验证描边、灯光阴影与TAA时不需要再打开源。
