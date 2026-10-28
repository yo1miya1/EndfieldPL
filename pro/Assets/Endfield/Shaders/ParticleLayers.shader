Shader "Endfield/ParticleLayers"
{
 Properties
 {
        _ParticleBlendCoverage("ParticleBlendCoverage",Vector)=(0,0,0,0)
        _ParticleColorStreamControls("ParticleColorStreamControls",Vector)=(0,0,0,0)
        _ParticleHighlightResponse("ParticleHighlightResponse",Vector)=(0,0,0,0)
        _ParticleExposureViewControls("ParticleExposureViewControls",Vector)=(0,0,0,0)
        _ParticlePrimaryTint("ParticlePrimaryTint",Vector)=(0,0,0,0)
        _ParticlePrimarySampling("ParticlePrimarySampling",Vector)=(0,0,0,0)
        _ParticleUvVelocity("ParticleUvVelocity",Vector)=(0,0,0,0)
        _ParticleUvRotation("ParticleUvRotation",Vector)=(0,0,0,0)
        _ParticleUvWeights("ParticleUvWeights",Vector)=(0,0,0,0)
        _ParticleUvTransform("ParticleUvTransform",Vector)=(0,0,0,0)
        _ParticleColorResponse("ParticleColorResponse",Vector)=(0,0,0,0)
        _ParticleNoiseSampling("ParticleNoiseSampling",Vector)=(0,0,0,0)
        _ParticleNoiseResponse("ParticleNoiseResponse",Vector)=(0,0,0,0)
        _ParticleCoverageControl("ParticleCoverageControl",Vector)=(0,0,0,0)
        _ParticleMaskUvControls("ParticleMaskUvControls",Vector)=(0,0,0,0)
        _ParticleMaskTint("ParticleMaskTint",Vector)=(0,0,0,0)
        _ParticleMaskSampling("ParticleMaskSampling",Vector)=(0,0,0,0)
        _ParticleMaskResponse("ParticleMaskResponse",Vector)=(0,0,0,0)
        _ParticleMaskCoverage("ParticleMaskCoverage",Vector)=(0,0,0,0)
        _ParticleSoftDepthControls("ParticleSoftDepthControls",Vector)=(0,0,0,0)
        _ParticleDepthFadeNear("ParticleDepthFadeNear",Vector)=(0,0,0,0)
        _ParticleDepthFadeFar("ParticleDepthFadeFar",Vector)=(0,0,0,0)
        _ParticleOutputTint("ParticleOutputTint",Vector)=(0,0,0,0)
        _ParticleLayerInfluence("ParticleLayerInfluence",Vector)=(0,0,0,0)
        _ParticleDistortionMode("ParticleDistortionMode",Vector)=(0,0,0,0)
        _ParticleDistortionScale("ParticleDistortionScale",Vector)=(0,0,0,0)
        _ParticleDistortionFlags("ParticleDistortionFlags",Vector)=(0,0,0,0)
        _ParticleSoftIntersection("ParticleSoftIntersection",Vector)=(0,0,0,0)
        _ParticleSecondaryLayerInfluence("ParticleSecondaryLayerInfluence",Vector)=(0,0,0,0)
        _ParticleSecondaryDistortionMode("ParticleSecondaryDistortionMode",Vector)=(0,0,0,0)
        _ParticleSecondaryDistortionScale("ParticleSecondaryDistortionScale",Vector)=(0,0,0,0)
        _ParticleSecondaryDistortionFlags("ParticleSecondaryDistortionFlags",Vector)=(0,0,0,0)
        _ParticleSecondarySampling("ParticleSecondarySampling",Vector)=(0,0,0,0)
        _ParticleOverlayInfluence("ParticleOverlayInfluence",Vector)=(0,0,0,0)
        _ParticleOverlayResponse("ParticleOverlayResponse",Vector)=(0,0,0,0)
        _ParticleOverlayTint("ParticleOverlayTint",Vector)=(0,0,0,0)
        _ParticleVertexStreamControl("ParticleVertexStreamControl",Vector)=(0,0,0,0)
        _ParticleVertexViewControl("ParticleVertexViewControl",Vector)=(0,0,0,0)
        _ParticleVertexColorControl("ParticleVertexColorControl",Vector)=(0,0,0,0)
        _PrimaryUvVelocity("PrimaryUvVelocity",Vector)=(0,0,0,0)
        _PrimaryUvRotation("PrimaryUvRotation",Vector)=(0,0,0,0)
        _PrimaryUvWeights("PrimaryUvWeights",Vector)=(0,0,0,0)
        _PrimaryUvTransform("PrimaryUvTransform",Vector)=(0,0,0,0)
        _MaskUvLayerWeights("MaskUvLayerWeights",Vector)=(0,0,0,0)
        _MaskUvVelocity("MaskUvVelocity",Vector)=(0,0,0,0)
        _MaskUvRotation("MaskUvRotation",Vector)=(0,0,0,0)
        _MaskUvWeights("MaskUvWeights",Vector)=(0,0,0,0)
        _NoiseUvLayerWeights("NoiseUvLayerWeights",Vector)=(0,0,0,0)
        _NoiseUvAdditionalWeight("NoiseUvAdditionalWeight",Vector)=(0,0,0,0)
        _NoiseUvVelocity("NoiseUvVelocity",Vector)=(0,0,0,0)
        _NoiseUvRotation("NoiseUvRotation",Vector)=(0,0,0,0)
        _NoiseUvWeights("NoiseUvWeights",Vector)=(0,0,0,0)
        _OverlayUvLayerWeights("OverlayUvLayerWeights",Vector)=(0,0,0,0)
        _OverlayUvVelocity("OverlayUvVelocity",Vector)=(0,0,0,0)
        _OverlayUvRotation("OverlayUvRotation",Vector)=(0,0,0,0)
        _OverlayUvWeights("OverlayUvWeights",Vector)=(0,0,0,0)
        _OverlayUvResponse("OverlayUvResponse",Vector)=(0,0,0,0)
        _OverlayUvTransform("OverlayUvTransform",Vector)=(0,0,0,0)
        _UvBaseTransformA("UvBaseTransformA",Vector)=(0,0,0,0)
        _UvBaseTransformB("UvBaseTransformB",Vector)=(0,0,0,0)
        _UvSharedTransformA("UvSharedTransformA",Vector)=(0,0,0,0)
        _UvSharedTransformB("UvSharedTransformB",Vector)=(0,0,0,0)
        _UvSharedTransformC("UvSharedTransformC",Vector)=(0,0,0,0)
        _UvExtraTransformA("UvExtraTransformA",Vector)=(0,0,0,0)
        _UvExtraTransformB("UvExtraTransformB",Vector)=(0,0,0,0)
        _UvExtraTransformC("UvExtraTransformC",Vector)=(0,0,0,0)
        _UvExtraTransformD("UvExtraTransformD",Vector)=(0,0,0,0)
        _UvExtraTransformE("UvExtraTransformE",Vector)=(0,0,0,0)
        _UvExtraTransformF("UvExtraTransformF",Vector)=(0,0,0,0)
        _ParticleInstanceCoverage("ParticleInstanceCoverage",Vector)=(0,0,0,0)
        _ParticleOutputColorResponse("ParticleOutputColorResponse",Vector)=(0,0,0,0)
        _ParticleVertexFade("ParticleVertexFade",Vector)=(0,0,0,0)
        _ParticleBaseMap("_ParticleBaseMap",2D)="white"{}
        _ParticleNoiseMap("_ParticleNoiseMap",2D)="white"{}
        _ParticleMaskMap("_ParticleMaskMap",2D)="white"{}
        _ParticleOverlayMap("_ParticleOverlayMap",2D)="white"{}
        _ParticleMipBias("_ParticleMipBias",Float)=0
        _ParticlePhase("_ParticlePhase",Float)=0
        _ParticlePhaseSpeed("_ParticlePhaseSpeed",Float)=0
        _ColorMask("_ColorMask",Float)=15
        _Cull("_Cull",Float)=0
        _ZWrite("_ZWrite",Float)=0
        _ZTest("_ZTest",Float)=4
        _SrcBlend("_SrcBlend",Float)=1
        _DstBlend("_DstBlend",Float)=10
        _SrcBlendAlpha("_SrcBlendAlpha",Float)=1
        _DstBlendAlpha("_DstBlendAlpha",Float)=10
        _BlendOp("_BlendOp",Float)=0
        _BlendOpAlpha("_BlendOpAlpha",Float)=0
        _StencilRef("_StencilRef",Float)=0
        _StencilReadMask("_StencilReadMask",Float)=255
        _StencilWriteMask("_StencilWriteMask",Float)=255
        _StencilComp("_StencilComp",Float)=8
        _StencilPass("_StencilPass",Float)=0
        _StencilFail("_StencilFail",Float)=0
        _StencilZFail("_StencilZFail",Float)=0
 }
 SubShader
 {
 Tags { "RenderPipeline"="EndfieldPipeline" "Queue"="Transparent" }
 Pass
 {
 Name "EndfieldForward" Tags { "LightMode"="EndfieldForward" }
 ColorMask [_ColorMask]
 Cull [_Cull] ZWrite [_ZWrite] ZTest [_ZTest]
 Blend [_SrcBlend] [_DstBlend],[_SrcBlendAlpha] [_DstBlendAlpha]
 BlendOp [_BlendOp],[_BlendOpAlpha]
 Stencil { Ref [_StencilRef] ReadMask [_StencilReadMask] WriteMask [_StencilWriteMask] Comp [_StencilComp] Pass [_StencilPass] Fail [_StencilFail] ZFail [_StencilZFail] }
 HLSLPROGRAM
 #pragma target 4.5
 #pragma vertex EFParticleVertex
 #pragma fragment EFParticleFragment
 #pragma shader_feature_local EF_PARTICLE_THREE_LAYER EF_PARTICLE_SOFT_LAYER EF_PARTICLE_FOUR_LAYER_SHIFT EF_PARTICLE_FOUR_LAYER EF_PARTICLE_REFRACTION
 #include "Library/Particles/ParticleInputs.hlsl"
#if defined(EF_PARTICLE_THREE_LAYER)
#include "Library/Particles/ThreeLayerFormula.hlsl"
#include "Library/Particles/ThreeLayerVertex.hlsl"
#elif defined(EF_PARTICLE_SOFT_LAYER)
#include "Library/Particles/SoftLayerFormula.hlsl"
#include "Library/Particles/SoftLayerVertex.hlsl"
#elif defined(EF_PARTICLE_FOUR_LAYER_SHIFT)
#include "Library/Particles/FourLayerShiftFormula.hlsl"
#include "Library/Particles/FourLayerShiftVertex.hlsl"
#elif defined(EF_PARTICLE_FOUR_LAYER)
#include "Library/Particles/FourLayerFormula.hlsl"
#include "Library/Particles/FourLayerVertex.hlsl"
#elif defined(EF_PARTICLE_REFRACTION)
#include "Library/Particles/RefractionFormula.hlsl"
#include "Library/Particles/RefractionVertex.hlsl"
#else
#include "Library/Particles/SoftLayerFormula.hlsl"
#include "Library/Particles/SoftLayerVertex.hlsl"
#endif
 ENDHLSL
 }
 }
}
