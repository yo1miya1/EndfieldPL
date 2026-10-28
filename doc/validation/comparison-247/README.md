# 247 实际RGB对照

Source与Unity均2560×1440，RGB直接比较；不作调色、对齐或alpha合成。UI重新开场景保存、真实N/T与Stencil方向、RT0-only描边顺序已修复。

全图MAE 5.529/255。

| 区域 | MAE/255 |
| --- | ---: |
| background_top | 1.999 |
| background_left | 3.524 |
| background_right | 3.088 |
| platform_left | 3.328 |
| character_face | 17.435 |
| character_dress | 14.892 |
| ink_left_stroke | 5.878 |
| ink_left_knot | 9.654 |

头发/额前仍是材质优先项。1165 PS78/1121证明Hair半球应读主法线图结果，已纠正此前误用几何法线；待同相机复拍确认。衣料剩余局部高光差异不能通过数值调亮或改粗糙度来抹平。
