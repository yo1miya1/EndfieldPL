using UnityEngine;
using UnityEngine.Rendering;

namespace Endfield.Rendering
{
    internal sealed class EndfieldOutlinePass : EndfieldRenderPass
    {
        public override string Name => "Outline";
        public override void Execute(EndfieldFrameData frame)
        {
            frame.command.SetRenderTarget(frame.targets.gbufferAttachments, new RenderTargetIdentifier(frame.targets.depthAttachment));
            frame.Flush();
            DrawGeometry(frame, "EndfieldOutline", RenderQueueRange.opaque, SortingCriteria.CommonOpaque);
        }
    }

    internal sealed class EndfieldGBufferPass : EndfieldRenderPass
    {
        public override string Name => "GBuffer";
        public override void Execute(EndfieldFrameData frame)
        {
            frame.command.SetRenderTarget(frame.targets.gbufferAttachments, new RenderTargetIdentifier(frame.targets.depthAttachment));
            frame.Flush();
            // 队列2500留给包围场景的远景几何：先画表面和轮廓，再用深度挡住远景。
            // 普通Geometry/AlphaTest队列仍在本批；调度不识别角色或来源事件。
            DrawGeometry(frame, "EndfieldGBuffer", new RenderQueueRange { lowerBound = 0, upperBound = 2499 }, SortingCriteria.CommonOpaque);
            // 局部附件轮廓必须在表面之后写入；保留法线、材质和运动向量附件。
            // 这类轮廓只修改颜色载荷，不能走前置的完整GBuffer挤出轮廓。
            frame.command.SetRenderTarget(frame.targets.gbufferAttachments[0], new RenderTargetIdentifier(frame.targets.depthAttachment));
            frame.Flush();
            DrawGeometry(frame, "EndfieldSurfaceOutline", RenderQueueRange.opaque, SortingCriteria.CommonOpaque);
            frame.command.SetRenderTarget(frame.targets.gbufferAttachments, new RenderTargetIdentifier(frame.targets.depthAttachment));
            frame.Flush();
            DrawGeometry(frame, "EndfieldGBuffer", new RenderQueueRange { lowerBound = 2500, upperBound = 2500 }, SortingCriteria.CommonOpaque);
            for (int index = 0; index < 5; index++) frame.command.SetGlobalTexture("_GBuffer" + index, frame.targets.gbuffer[index]);
            frame.command.SetGlobalTexture("_CameraDepthTexture", new RenderTargetIdentifier(frame.targets.depthAttachment), RenderTextureSubElement.Depth);
        }
    }

    internal sealed class EndfieldTransparentPass : EndfieldRenderPass
    {
        readonly ShaderTagId[] shaderTags = { new ShaderTagId("EndfieldForward"), new ShaderTagId("EndfieldEffect") };
        public override string Name => "Transparent";
        public override void Execute(EndfieldFrameData frame)
        {
            if (frame.settings.requireOpaqueDepthTexture) frame.targets.CopyOpaqueDepthForSampling(frame.command);
            frame.command.SetRenderTarget(new RenderTargetIdentifier(frame.targets.sceneColor), new RenderTargetIdentifier(frame.targets.depthAttachment));
            frame.Flush();
            if (frame.camera.clearFlags == CameraClearFlags.Skybox && RenderSettings.skybox)
            {
                frame.command.DrawRendererList(frame.context.CreateSkyboxRendererList(frame.camera));
                frame.Flush();
            }
            // 多个候选标签仍在同一RendererList排序，避免把不同透明材质拆成两批。
            DrawGeometry(frame, shaderTags, RenderQueueRange.transparent, SortingCriteria.CommonTransparent);
        }
    }

    internal sealed class EndfieldUIPass : EndfieldRenderPass
    {
        public override string Name => "UI";
        public override void Execute(EndfieldFrameData frame)
        {
            // 调试视图展示中间结果；不能被整屏UI composition覆盖。
            if (frame.debugView != EndfieldDebugView.Final) return;
#if UNITY_EDITOR
            if (UnityEditor.Handles.ShouldRenderGizmos())
            {
                frame.context.DrawGizmos(frame.camera, GizmoSubset.PostImageEffects);
            }
#endif
            // 最终颜色已落到相机目标；UI直接使用Unity的原生方向、Canvas排序及裁剪。
            // 不把UI烘进sceneColor，避免曝光和最终RT翻转作用到界面。
            if (frame.camera.cameraType == CameraType.Game)
            {
                Endfield.UI.EndfieldViewportUIRenderer.Draw(frame.command, frame.camera);
                frame.command.DrawRendererList(frame.context.CreateUIOverlayRendererList(frame.camera));
                frame.Flush();
            }
        }
    }
}
