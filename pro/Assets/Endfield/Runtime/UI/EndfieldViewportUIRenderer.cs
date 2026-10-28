using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Experimental.Rendering;

namespace Endfield.UI
{
    // UI在独立UNORM层按源显示RGB混合，最后一次解码回线性相机目标。
    // 组合配置由当前相机引用，不通过Resources或角色名寻找全局配置。
    public static class EndfieldViewportUIRenderer
    {
        static readonly int Composite = Shader.PropertyToID("_EndfieldUICompositionTarget");
        static readonly int OutputScaleBias = Shader.PropertyToID("_EndfieldOutputScaleBias");
        static readonly int[] BlurStages = {
            Shader.PropertyToID("_EndfieldUIBlurStage0"), Shader.PropertyToID("_EndfieldUIBlurStage1"),
            Shader.PropertyToID("_EndfieldUIBlurStage2") };
        public static void Draw(CommandBuffer command, Camera camera)
        {
            if (!camera || camera.cameraType != CameraType.Game) return;
            var binding = camera.GetComponent<EndfieldUIComposition>();
            if (!binding || !binding.composition) return;
            var composition = binding.composition;
            if (!composition.compositeMaterial) return;
            int width = Mathf.Max(1, camera.pixelWidth), height = Mathf.Max(1, camera.pixelHeight);
            var descriptor = new RenderTextureDescriptor(width, height)
            {
                graphicsFormat = GraphicsFormat.R8G8B8A8_UNorm,
                depthStencilFormat = GraphicsFormat.D24_UNorm_S8_UInt,
                msaaSamples = 1,
                useMipMap = false,
                mipCount = 1
            };
            command.GetTemporaryRT(Composite, descriptor, FilterMode.Bilinear);
            command.SetRenderTarget(new RenderTargetIdentifier(Composite));
            command.SetViewport(new Rect(0, 0, width, height));
            // 源UI顶点始终画进同一个内部RT，不能提前套最终backbuffer的方向适配。
            command.SetGlobalVector(OutputScaleBias, new Vector4(1, 1, 0, 0));
            command.ClearRenderTarget(true, false, Color.clear, 1);
            command.DrawProcedural(Matrix4x4.identity, composition.compositeMaterial, 0, MeshTopology.Triangles, 3, 1);
            int blurStages = composition.sceneBlurMaterial && composition.sceneBlurDownsamples != null
                ? Mathf.Min(BlurStages.Length, composition.sceneBlurDownsamples.Length) : 0;
            // 源模糊在displayRGB空间运行；Composite初始化已经编码一次，后续不重复编码。
            // 每层使用当前分辨率按来源比例缩小，依次保留源高亮限制、half采样与二项核。
            for (int stage = 0; stage < blurStages; stage++)
            {
                int divisor = Mathf.Max(1, composition.sceneBlurDownsamples[stage]);
                int bw = Mathf.Max(1, width / divisor), bh = Mathf.Max(1, height / divisor);
                var blurDescriptor = descriptor;
                blurDescriptor.width = bw;
                blurDescriptor.height = bh;
                blurDescriptor.graphicsFormat = GraphicsFormat.B10G11R11_UFloatPack32;
                blurDescriptor.depthStencilFormat = GraphicsFormat.None;
                command.GetTemporaryRT(BlurStages[stage], blurDescriptor, FilterMode.Bilinear);
                command.SetGlobalTexture("_SourceTexture", stage == 0 ? Composite : BlurStages[stage - 1]);
                command.SetRenderTarget(BlurStages[stage]);
                command.SetViewport(new Rect(0, 0, bw, bh));
                var properties = new MaterialPropertyBlock();
                properties.SetVector("_SourceScaleBias", new Vector4(1, 1, 0, 0));
                // 源cb0[0].zw是本层输出网格尺寸的倒数，不是输入纹理尺寸。
                properties.SetVector("_SourceTexture_TexelSize", new Vector4(1f / bw, 1f / bh, bw, bh));
                properties.SetFloat("_UIBlurHighlightClamp", composition.sceneBlurHighlightClamp);
                command.DrawProcedural(Matrix4x4.identity, composition.sceneBlurMaterial,
                    composition.sceneBlurMaterial.FindPass("SourceUIBlur"), MeshTopology.Triangles, 3, 1, properties);
            }
            if (blurStages > 0)
                command.SetGlobalTexture("_EndfieldUIBlurredSceneTexture", BlurStages[blurStages - 1]);
            command.SetRenderTarget(Composite);
            command.SetViewport(new Rect(0, 0, width, height));
            foreach (var draw in composition.draws)
            {
                if (!draw.mesh || !draw.material) continue;
                if (draw.scissorEnabled)
                {
                    var rect = draw.scissor;
                    float sx = camera.pixelWidth / (float)composition.referenceResolution.x;
                    float sy = camera.pixelHeight / (float)composition.referenceResolution.y;
                    command.EnableScissorRect(new Rect(rect.x * sx, rect.y * sy, rect.width * sx, rect.height * sy));
                }
                command.DrawMesh(draw.mesh, Matrix4x4.identity, draw.material, 0, 0);
                if (draw.scissorEnabled) command.DisableScissorRect();
            }
            // 只有最终合成采样才根据Camera目标调整；内部UI与离屏截图保持同一方向。
            bool flip = SystemInfo.graphicsUVStartsAtTop && camera.targetTexture == null;
            command.SetGlobalVector(OutputScaleBias, flip ? new Vector4(1, -1, 0, 1) : new Vector4(1, 1, 0, 0));
            command.SetGlobalTexture("_EndfieldUICompositionTexture", Composite);
            command.SetRenderTarget(camera.targetTexture ? new RenderTargetIdentifier(camera.targetTexture) : new RenderTargetIdentifier(BuiltinRenderTextureType.CameraTarget));
            command.SetViewport(camera.pixelRect);
            command.DrawProcedural(Matrix4x4.identity, composition.compositeMaterial, 1, MeshTopology.Triangles, 3, 1);
            for (int stage = 0; stage < blurStages; stage++) command.ReleaseTemporaryRT(BlurStages[stage]);
            command.ReleaseTemporaryRT(Composite);
        }
    }
}
