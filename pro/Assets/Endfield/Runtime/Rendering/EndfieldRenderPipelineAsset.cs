using UnityEngine;
using UnityEngine.Rendering;

namespace Endfield.Rendering
{
    public enum EndfieldDebugView {
        Final, Emission, Motion, Material, Normal, Roughness, BaseColor, Depth, Shadow, RawShadow
    }

    [CreateAssetMenu(menuName = "Rendering/Endfield Pipeline", fileName = "EndfieldPipeline")]
    public sealed class EndfieldRenderPipelineAsset : RenderPipelineAsset<EndfieldRenderPipeline>
    {
        [Header("画面")]
        [Range(0.25f, 2f)] public float renderScale = 1f;
        public bool enableSrpBatcher = true;
        public EndfieldDebugView debugView;
        [Header("时序抗锯齿")]
        public bool enableTemporalAA = true;
        [Range(.01f, 1f)] public float temporalCurrentWeight = .1f;
        [Range(.01f, 3f)] public float temporalVarianceScale = .9f;
        public Shader temporalAAShader;
        [Header("实时光源")]
        [Range(0, 32)] public int maxAdditionalLights = 32;
        [Tooltip("仅在场景透明材质实际采样opaque深度时开启；附件与采样副本分离。")]
        public bool requireOpaqueDepthTexture;
        [Tooltip("在透明队列3500之前复制当前HDR颜色，供3500及之后的折射材质读取，避免读写同一附件。")]
        public bool requireRefractionColorTexture;
        [Min(1f)] public float shadowDistance = 80f;
        [Range(256, 4096)] public int shadowAtlasSize = 2048;
        [Range(1, 4)] public int shadowCascadeCount = 4;
        public Vector3 shadowCascadeSplits = new Vector3(0.1f, 0.3f, 0.6f);
        [Range(256, 4096)] public int additionalShadowAtlasSize = 2048;
        [Header("构建时显式保留全屏着色器")]
        public Shader deferredLightingShader;
        public Shader postProcessShader;
        public Shader colorLutShader;
        [Header("默认材质与Volume")]
        public Material defaultLitMaterial;
        public VolumeProfile defaultVolumeProfile;

        public override string renderPipelineShaderTag => "EndfieldPipeline";
        public override Material defaultMaterial => defaultLitMaterial;
        public override Shader defaultShader => defaultLitMaterial ? defaultLitMaterial.shader : Shader.Find("Endfield/HybridLit");
        protected override RenderPipeline CreatePipeline() => new EndfieldRenderPipeline(this);
    }
}
