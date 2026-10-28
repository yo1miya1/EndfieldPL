# Game视口UI方向修复

2026-10-28，用户确认真实编辑器Game视口的场景方向正确，而整层UI上下颠倒。此前282的离屏`Camera.targetTexture`图方向正常，不能据此替代真实Game视口验收。

问题在`EndfieldViewportUIRenderer.Draw`：7类源UI顶点程序读取`_EndfieldOutputScaleBias.y`，绘制目标却始终是内部Composition RT。没有`camera.targetTexture`时，该变量提前包含backbuffer的-1方向；最后Composite Resolve又执行目标适配，导致UI相对场景翻转。

修复仅改UI调度：绘制内部Composition时设scale/bias为(1,1,0,0)，最终Resolve前再恢复相机目标的方向。相对于旧Game视口，这等价于UI整体Y乘-1；离屏路径保持原样，场景、后处理和7类材质的源计算不变。

验收包含两种来源：

- Unity API读取真实`GameView.m_RenderTexture`，实际`Camera.main.targetTexture == null`，未另做Camera.Render。原始读回为`tmp/unity/game-view/20261028-154534-444/game-view.png`；其原生RT行序使整张场景和UI同时倒置，二者方向一致。此图不是最终GUI显示截图，不能再拿它给UI单独翻转。
- 用户随后提供真实编辑器截图并明确确认“编辑器内是正确的了”。原图保存在`ui-game-view-confirmed.png`，场景正向，标题/货币在顶部，底栏在底部，所有文字方向正常。

此修复已保留在运行时目录，和Authoring截图工具是否存在无关。295最新Windows构建已包含修复，结果Succeeded、errors=0；用户随后确认其他功能无大问题，本轮完成收尾。
