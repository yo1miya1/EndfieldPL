using UnityEngine;
using UnityEngine.Rendering;

namespace Endfield.Editor
{
    /// <summary>创作和离线发布共用的材质Pass选择；运行时不判断来源对象或事件号。</summary>
    public static class EndfieldMaterialSetup
    {
        public static void Apply(Material material)
        {
            if (!material || material.shader.name != "Endfield/HybridLit") return;

            bool opaque = material.renderQueue <= (int)RenderQueue.GeometryLast;
            bool character = material.IsKeywordEnabled("EF_SOURCE_CHARACTER");
            bool effect = material.IsKeywordEnabled("EF_SOURCE_EFFECT");
            bool outline = opaque && material.GetFloat("_OutlineWidth") >= .000001f;
            bool surfaceOutline = opaque && material.IsKeywordEnabled("EF_SOURCE_SCREEN_OUTLINE") && material.GetFloat("_SourceOutlineWidth") > 0;

            // SetShaderPassEnabled使用LightMode标签，与RendererList的选择契约相同。
            material.SetShaderPassEnabled("EndfieldGBuffer", opaque && !effect);
            material.SetShaderPassEnabled("EndfieldSurfaceLighting", opaque && character && !effect);
            material.SetShaderPassEnabled("EndfieldEffect", effect);
            material.SetShaderPassEnabled("EndfieldForward", !opaque && !effect);
            material.SetShaderPassEnabled("EndfieldOutline", outline && !surfaceOutline);
            material.SetShaderPassEnabled("EndfieldSurfaceOutline", surfaceOutline);
            material.SetShaderPassEnabled("EndfieldMotionVectors", opaque);
            // ShadowCaster由Renderer.shadowCastingMode决定，不能把材质家族当作投影开关。
        }
    }
}
