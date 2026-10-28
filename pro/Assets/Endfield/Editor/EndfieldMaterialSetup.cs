using UnityEngine;
using UnityEngine.Rendering;

namespace Endfield.Editor
{
    /// <summary>创作和离线发布共用的材质Pass选择；运行时不判断来源对象或事件号。</summary>
    public static class EndfieldMaterialSetup
    {
        // 持久材质语义：GB=1、Surface=2、Forward=4、GB轮廓=8、通用轮廓=16、
        // 主阴影=32、角色阴影=64、Motion=128、Effect=256。0沿创作模型自动选择。
        static readonly string[] PassTags = { "EndfieldGBuffer", "EndfieldSurfaceLighting", "EndfieldForward",
            "EndfieldSurfaceOutline", "EndfieldOutline", "ShadowCaster", "CharacterShadowCaster",
            "EndfieldMotionVectors", "EndfieldEffect" };
        public static void Apply(Material material)
        {
            if (!material || material.shader.name != "Endfield/HybridLit") return;
            int passMask = Mathf.RoundToInt(material.GetFloat("_RenderPassMask"));
            if (passMask != 0)
            {
                for (int index = 0; index < PassTags.Length; index++)
                    material.SetShaderPassEnabled(PassTags[index], (passMask & (1 << index)) != 0);
                return;
            }

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
            material.SetShaderPassEnabled("ShadowCaster", true);
            material.SetShaderPassEnabled("CharacterShadowCaster", true);
            // ShadowCaster由Renderer.shadowCastingMode决定，不能把材质家族当作投影开关。
        }
    }
}
