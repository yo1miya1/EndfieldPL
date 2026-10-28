# 232 实际RGB对照

Source与Unity均2560×1440，丢弃附带alpha，不作透明合成、对齐或调色。Unity为主代理232 Game实际截帧，静态N/T方向已按源PostVS修正；主相机、Light、Probe仍由Unity运行时提供。

全图RGB MAE：5.559/255。

| 区域 | MAE/255 |
| --- | ---: |
| background_top | 1.998 |
| background_left | 3.523 |
| background_right | 3.089 |
| platform_left | 3.343 |
| character_face | 19.019 |
| character_dress | 14.793 |
| ink_left_stroke | 5.884 |
| ink_left_knot | 9.639 |

优先级：头发/额前轮廓偏黑（Face ROI平均RGB约暗13）高于背景残差；需先验证额外OutlineColor SceneColor=0是否真对应源RT0-only语义。随后核衣料局部高光/暗部计算。此指标含边缘/特效覆盖差异，不应当作材质亮度校准值。
