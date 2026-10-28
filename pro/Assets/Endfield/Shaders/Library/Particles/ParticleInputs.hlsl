#ifndef ENDFIELD_PARTICLE_INPUTS
#define ENDFIELD_PARTICLE_INPUTS
#include "../Coordinates.hlsl"
TEXTURE2D(_ParticleBaseMap); TEXTURE2D(_ParticleNoiseMap); TEXTURE2D(_ParticleMaskMap); TEXTURE2D(_ParticleOverlayMap);
TEXTURE2D(_CameraDepthTexture); TEXTURE2D(_CameraRefractionTexture);
SAMPLER(sampler_ParticleLinearRepeat); SAMPLER(sampler_ParticleLinearClamp); SAMPLER(sampler_ParticlePointClamp);
float4 _Time; float4 unity_OrthoParams; float _EndfieldSceneExposure;
// 当前相机列向量只用于数值叶的原矩阵乘加，不是可序列化的源常量页。
uint4 EFParticleInverseViewColumn(int axis) { return asuint(transpose(_EndfieldInverseViewProjection)[axis]); }
uint4 EFParticleViewColumn(int axis) { return asuint(transpose(unity_MatrixV)[axis]); }
CBUFFER_START(UnityPerMaterial)
float4 _ParticleBlendCoverage;
float4 _ParticleColorStreamControls;
float4 _ParticleHighlightResponse;
float4 _ParticleExposureViewControls;
float4 _ParticlePrimaryTint;
float4 _ParticlePrimarySampling;
float4 _ParticleUvVelocity;
float4 _ParticleUvRotation;
float4 _ParticleUvWeights;
float4 _ParticleUvTransform;
float4 _ParticleColorResponse;
float4 _ParticleNoiseSampling;
float4 _ParticleNoiseResponse;
float4 _ParticleCoverageControl;
float4 _ParticleMaskUvControls;
float4 _ParticleMaskTint;
float4 _ParticleMaskSampling;
float4 _ParticleMaskResponse;
float4 _ParticleMaskCoverage;
float4 _ParticleSoftDepthControls;
float4 _ParticleDepthFadeNear;
float4 _ParticleDepthFadeFar;
float4 _ParticleOutputTint;
float4 _ParticleLayerInfluence;
float4 _ParticleDistortionMode;
float4 _ParticleDistortionScale;
float4 _ParticleDistortionFlags;
float4 _ParticleSoftIntersection;
float4 _ParticleSecondaryLayerInfluence;
float4 _ParticleSecondaryDistortionMode;
float4 _ParticleSecondaryDistortionScale;
float4 _ParticleSecondaryDistortionFlags;
float4 _ParticleSecondarySampling;
float4 _ParticleOverlayInfluence;
float4 _ParticleOverlayResponse;
float4 _ParticleOverlayTint;
float4 _ParticleVertexStreamControl;
float4 _ParticleVertexViewControl;
float4 _ParticleVertexColorControl;
float4 _PrimaryUvVelocity;
float4 _PrimaryUvRotation;
float4 _PrimaryUvWeights;
float4 _PrimaryUvTransform;
float4 _MaskUvLayerWeights;
float4 _MaskUvVelocity;
float4 _MaskUvRotation;
float4 _MaskUvWeights;
float4 _NoiseUvLayerWeights;
float4 _NoiseUvAdditionalWeight;
float4 _NoiseUvVelocity;
float4 _NoiseUvRotation;
float4 _NoiseUvWeights;
float4 _OverlayUvLayerWeights;
float4 _OverlayUvVelocity;
float4 _OverlayUvRotation;
float4 _OverlayUvWeights;
float4 _OverlayUvResponse;
float4 _OverlayUvTransform;
float4 _UvBaseTransformA;
float4 _UvBaseTransformB;
float4 _UvSharedTransformA;
float4 _UvSharedTransformB;
float4 _UvSharedTransformC;
float4 _UvExtraTransformA;
float4 _UvExtraTransformB;
float4 _UvExtraTransformC;
float4 _UvExtraTransformD;
float4 _UvExtraTransformE;
float4 _UvExtraTransformF;
float4 _ParticleInstanceCoverage;
float4 _ParticleOutputColorResponse;
float4 _ParticleVertexFade;
float _ParticleMipBias,_ParticlePhase,_ParticlePhaseSpeed;
CBUFFER_END
struct EFParticleAttributes { float3 positionOS:POSITION;float3 normalOS:NORMAL;float4 tangentOS:TANGENT;float2 uv:TEXCOORD0;float4 color:COLOR;float4 extra0:TEXCOORD3;float4 extra1:TEXCOORD4;float4 extra2:TEXCOORD5; };
struct EFParticleUnityBasis { float4 position,currentClip,previousClip;float3 world,normal;float4 tangent;float2 uv;float3 deformationWorldDelta; };
EFParticleUnityBasis EFParticleBuildUnityBasis(EFParticleAttributes input)
{
 EFParticleUnityBasis b=(EFParticleUnityBasis)0; b.world=EFWorldPosition(input.positionOS);b.normal=EFWorldNormal(input.normalOS);
 b.currentClip=EFClipPosition(b.world);b.position=b.currentClip;b.previousClip=mul(_EndfieldPreviousViewProjection,float4(b.world,1));b.uv=input.uv;return b;
}
#endif
