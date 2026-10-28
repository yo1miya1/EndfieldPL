using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace Endfield.Rendering
{
    internal sealed class EndfieldTemporalAAPass : EndfieldRenderPass
    {
        public override string Name => "TemporalAA";
        readonly int motion = Shader.PropertyToID("_TemporalMotionTexture");
        readonly int resolved = Shader.PropertyToID("_TemporalResolvedColor");

        public override void Execute(EndfieldFrameData frame)
        {
            if (!frame.temporalEnabled) return;
            var command = frame.command;
            int width = frame.targets.width, height = frame.targets.height;
            command.GetTemporaryRT(motion, new RenderTextureDescriptor(width, height)
            {
                graphicsFormat = GraphicsFormat.R16G16_SFloat,
                depthStencilFormat = GraphicsFormat.None, msaaSamples = 1
            }, FilterMode.Point);
            frame.targets.RegisterEffect(motion);
            frame.targets.AllocateEffect(command, resolved, width, height);
            command.SetGlobalTexture("_SourceTexture", frame.targets.sceneColor);
            command.SetGlobalVector("_SourceTexture_TexelSize", new Vector4(1f / width, 1f / height, width, height));
            command.SetGlobalFloat("_TemporalHistoryValid", frame.temporalHistory.valid ? 1 : 0);
            command.SetGlobalFloat("_TemporalCurrentWeight", frame.settings.temporalCurrentWeight);
            command.SetGlobalFloat("_TemporalVarianceScale", frame.settings.temporalVarianceScale);
            command.SetGlobalTexture("_TemporalHistoryTexture", frame.temporalHistory.color);
            command.SetRenderTarget(motion);
            command.SetViewport(new Rect(0, 0, width, height));
            // 先重建全屏camera motion，再以Unity当前/前帧模型矩阵覆盖动态不透明网格。
            Fullscreen(frame, frame.temporalMaterial, 1);
            command.SetRenderTarget(new RenderTargetIdentifier(motion), new RenderTargetIdentifier(frame.targets.depthAttachment));
            frame.Flush();
            DrawGeometry(frame, "EndfieldMotionVectors", RenderQueueRange.opaque, SortingCriteria.CommonOpaque);
            command.SetGlobalTexture("_TemporalMotionTexture", motion);
            command.SetRenderTarget(resolved);
            Fullscreen(frame, frame.temporalMaterial, 0);
            command.CopyTexture(new RenderTargetIdentifier(resolved), new RenderTargetIdentifier(frame.temporalHistory.color));
            frame.postProcessSource = resolved;
            frame.Flush();
        }
    }
}
