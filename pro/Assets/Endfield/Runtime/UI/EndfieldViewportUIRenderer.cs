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
            command.ReleaseTemporaryRT(Composite);
        }
    }
}
