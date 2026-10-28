using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.Rendering.RendererUtils;

namespace Endfield.Rendering
{
    internal abstract class EndfieldRenderPass
    {
        public abstract string Name { get; }
        public abstract void Execute(EndfieldFrameData frame);

        protected static void DrawGeometry(EndfieldFrameData frame, string tag, RenderQueueRange range, SortingCriteria sorting)
        {
            DrawGeometry(frame, new[] { new ShaderTagId(tag) }, range, sorting);
        }

        protected static void DrawGeometry(EndfieldFrameData frame, ShaderTagId[] tags, RenderQueueRange range, SortingCriteria sorting)
        {
            var description = new RendererListDesc(tags, frame.culling, frame.camera)
            {
                renderQueueRange = range, sortingCriteria = sorting, layerMask = frame.camera.cullingMask,
                // 和Unity Forward原生路径一致，LightData与ReflectionProbes一起请求。
                rendererConfiguration = PerObjectData.Lightmaps | PerObjectData.LightProbe
                    | PerObjectData.ReflectionProbes | PerObjectData.LightData | PerObjectData.MotionVectors
            };
            frame.command.DrawRendererList(frame.context.CreateRendererList(description));
            frame.Flush();
        }

        protected static void Fullscreen(EndfieldFrameData frame, Material material, int pass)
        {
            if (material) frame.command.DrawProcedural(Matrix4x4.identity, material, pass, MeshTopology.Triangles, 3);
        }
    }
}
