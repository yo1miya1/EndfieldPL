# 编辑器崩溃记录（2026-10-27）

03:57 左右，命令 `034-scene-no-post` 在真实 SceneView 相机上进行 RenderDoc 截帧时，Unity 6000.6.3f1 退出。之前普通 Game/Scene PNG 截图均已返回成功。

日志末尾的原生调用栈位于 `amdxx64.dll`，当前只能确定失败发生在显卡驱动线程，不能据此断言是驱动版本、Shader 或 RenderDoc 的单独问题。日志保存于 `tmp/unity/editor-crash-20261027.log`；系统报告目录为 `C:/Users/Yoimiya/AppData/Local/Temp/Unity/Editor/Crashes/Crash_2026-10-26_185742820`。

恢复策略：重新启动原工程，先用普通实际相机截图隔离画面问题；RenderDoc 验收仍保留，后续在主相机上执行，不重复同一失败请求。没有提交报告或修改显卡驱动。

后续实际回放发现主线程的RenderDoc起止调用可能只截到渲染线程的帧尾。截帧器已在预热后及EndCapture前同步GPU回读；077、083、086均得到包含角色、后处理与UI的完整帧。这修复了已证实的捕获边界问题，不据此宣称找到了原驱动崩溃的唯一原因。

另一次编辑器停滞发生在新增材质Inspector时的API Updater阶段，进程没有退出但命令队列停止推进。已改用Unity 6的MaterialProperty.propertyFlags/ShaderPropertyFlags，并从命令行恢复保存的场景；没有通过桌面自动化处理弹窗。当前日志为 `tmp/unity/editor-active.log`。
