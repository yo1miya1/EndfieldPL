# 259 Hair源半球修正后的实际RGB对照

Source与Unity均2560×1440，RGB直接比较，无调色、对齐或alpha合成。只有已确认的Hair半球输入由几何法线改回源主法线图；全部材质参数保持原值。

全图MAE 5.531/255（247为5.529），基本持平，未据此宣称视觉残差已解决。

| 区域 | MAE/255 |
| --- | ---: |
| background_top | 1.994 |
| background_left | 3.519 |
| background_right | 3.084 |
| platform_left | 3.310 |
| character_face | 17.547 |
| character_dress | 14.927 |
| ink_left_stroke | 5.883 |
| ink_left_knot | 9.643 |

head-source-247-259-rgb.png为原RGB头部同框三列，不resize。残余重点仍是头发/额前明暗和轮廓、衣料局部镜面与阴影/时间重建，需隔离producer或源公式进一步取证；不能根据宽泛MAE回退原式或调参数补偿。
