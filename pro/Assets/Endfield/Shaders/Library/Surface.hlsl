#ifndef ENDFIELD_SURFACE_INCLUDED
#define ENDFIELD_SURFACE_INCLUDED
#include "GBuffer.hlsl"
#include "CharacterShadows.hlsl"
TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
TEXTURE2D(_NormalMap); SAMPLER(sampler_NormalMap);
TEXTURE2D(_MaskMap); SAMPLER(sampler_MaskMap);
TEXTURE2D(_EmissionMap); SAMPLER(sampler_EmissionMap);
TEXTURE2D(_CoverageMap); SAMPLER(sampler_CoverageMap);
TEXTURE2D(_SourceMaskMap); SAMPLER(sampler_SourceMaskMap);
TEXTURE2D(_LightingRamp); SAMPLER(sampler_LightingRamp);
TEXTURE2D(_AlbedoResponseLut); SAMPLER(sampler_AlbedoResponseLut);
TEXTURE2D(_EnvironmentMaskMap); SAMPLER(sampler_EnvironmentMaskMap);
TEXTURE2D(_HairMaskMap); SAMPLER(sampler_HairMaskMap);
TEXTURE2D(_HairNormalMap); SAMPLER(sampler_HairNormalMap);
TEXTURE2D(_HairSpecularRamp); SAMPLER(sampler_HairSpecularRamp);
TEXTURE2D(_HairOcclusionMap); SAMPLER(sampler_HairOcclusionMap);
TEXTURE2D(_EyeReflectionMap); SAMPLER(sampler_EyeReflectionMap);
TEXTURE2D(_ClothCoatMaskMap); SAMPLER(sampler_ClothCoatMaskMap);
TEXTURE2D(_ClothCoatReflectanceMap); SAMPLER(sampler_ClothCoatReflectanceMap);
TEXTURE2D(_AlphaMap); SAMPLER(sampler_AlphaMap);
TEXTURE2D(_SkinRegionMap); SAMPLER(sampler_SkinRegionMap);
TEXTURE2D(_SkinLightingSdf); SAMPLER(sampler_SkinLightingSdf);
TEXTURE2D(_SkinSpecularMap); SAMPLER(sampler_SkinSpecularMap);
TEXTURE2D(_ParallaxGlowMap); SAMPLER(sampler_ParallaxGlowMap);
TEXTURE2D(_SourceOutlineWidthMap); SAMPLER(sampler_SourceOutlineWidthMap);
TEXTURE2D(_SourceOutlineCoverageMap); SAMPLER(sampler_SourceOutlineCoverageMap);
CBUFFER_START(UnityPerMaterial)
float4 _BaseMap_ST;
float4 _BaseColor;
float4 _EmissionColor;
float4 _OutlineColor;
float _NormalScale;
float _Metallic;
float _Roughness;
float _Occlusion;
float _Specular;
float _NprWeight;
float _Cutoff;
float _OutlineWidth;
float _SourceOutlineWidth;
float _SourceOutlineDepth;
float _SourceOutlineSmoothNormal;
float _SourceOutlineCutoff;
float _Cull;
float _SrcBlend;
float _DstBlend;
float _ZWrite;
float4 _SourceInstancePayload;
float _CharacterShadowIndex;
float4 _ViewTintColor;
float _ViewTintStrength;
float _BackFaceNormal;
float _SourceMipBias;
float _SourceGBufferTag;
float _SourceIndirectAlbedoGain;
float _SourceIndirectSaturation;
float _SourceRampBias;
float _SourceIndirectStrength;
float _SourceDiffuseStrength;
float _SourceSpecularStrength;
float _SourceShadowStrength;
float4 _SourceAmbientTint;
float4 _SourceHemisphereDirection;
float4 _SourceHemisphereParams;
float4 _SourceEnvironmentRotation;
float _SourceAmbientResponse;
float _SourceDirectColorWeight;
float _SourceEnvironmentStrength;
float4 _SkinRightOS;
float4 _SkinForwardOS;
float4 _SkinViewTintStrength;
float4 _SkinHemisphereOriginOS;
float4 _SkinSpecularParallax;
float _SkinSdfBias;
float4 _ParallaxGlowParams;
float4 _ParallaxGlowColor;
float4 _ParallaxGlowMap_ST;
float4 _EnvironmentBaseUV_ST;
float4 _EnvironmentMaterialUV_ST;
float4 _EnvironmentRoughnessRange;
float _EnvironmentAlbedoUVWeight;
float _EnvironmentMaterialUVWeight;
float _EnvironmentMetallicOverrideWeight;
float _EnvironmentMetallicOverride;
float _EnvironmentBaseGain;
float _EnvironmentBaseBlend;
float _EnvironmentSpecularRoughnessWeight;
float _EnvironmentSpecularBias;
float _EnvironmentSpecularMetallicWeight;
float _EnvironmentLightingWeight;
float _EnvironmentReflectionMask;
float _EnvironmentMotionDisabled;
float _EnvironmentNormalMipBias;
float _EnvironmentMaterialTag;
float4 _HairPrimarySecondaryShift;
float4 _HairSecondaryColor;
float _HairPrimaryStrength;
float _HairSecondarySmoothness;
float _HairFlowDirection;
float _HairDetailNormalScale;
float _HairViewAlignmentPower;
float4 _HairRightOS;
float4 _HairForwardOS;
float4 _HairOcclusionLobe;
float4 _HairOcclusionResponse;
float4 _HairOcclusionMap_ST;
float4 _EffectVertexColor;
float4 _EffectColor;
float4 _EffectDissolveColor;
float4 _EffectDepthRanges;
float4 _EffectDissolveProfile;
float4 _EffectColorResponse;
float _EffectIgnoreVertexColor;
float _EffectColorIntensity;
float _EffectAlphaIntensity;
float _EffectMonochromeWeight;
float _EffectMipBias;
float _EffectInvisibleWeight;
float _EffectDissolveEnabled;
float _EffectDissolveMask;
float _EffectDissolveStrength;
float _EffectDissolveHeight;
float _EffectBloomThreshold;
float _EffectBloomBoost;
float _EffectPreExposureWeight;
float _EffectDepthFadeEnabled;
float _EffectInstanceOpacity;
float _EffectOpacity;
float _EffectAlphaMode;
float _EffectColorResponseWeight;
float4 _EyeIrisTint;
float4 _EyeScleraTint;
float4 _EyeReflectionColor;
float _EyeReflectionStrength;
float _EyeParallax;
float _EyeCurvature;
float4 _ClothAnisotropy;
float _ClothTangentMode;
float4 _ClothSecondLobeColor;
float4 _ClothCoatColor;
float _ClothCoatSmoothness;
float _ClothCoatMetallic;
float _ClothCoatNormalBlend;
float _Opacity;
CBUFFER_END
struct EFAttributes
{
    float3 positionOS : POSITION;
    float3 normalOS : NORMAL;
    float4 tangentOS : TANGENT;
    float2 uv : TEXCOORD0;
    float2 uv1 : TEXCOORD1;
    float2 outlineNormalTS : TEXCOORD2;
};
struct EFVaryings
{
    float4 positionCS : SV_POSITION;
    float3 positionWS : TEXCOORD0;
    float3 normalWS : TEXCOORD1;
    float4 tangentWS : TEXCOORD2;
    float2 uv : TEXCOORD3;
    float4 currentClip : TEXCOORD4;
    float2 uv1 : TEXCOORD5;
};
EFVaryings EFVertex(EFAttributes input)
{
    EFVaryings o;
    o.positionWS = EFWorldPosition(input.positionOS);
    o.positionCS = EFClipPosition(o.positionWS);
    o.currentClip = mul(_EndfieldNonJitteredViewProjection, float4(o.positionWS, 1));
    o.normalWS = EFWorldNormal(input.normalOS);
    o.tangentWS = float4(EFWorldTangent(input.tangentOS.xyz), input.tangentOS.w * unity_WorldTransformParams.w);
    o.uv = input.uv * _BaseMap_ST.xy + _BaseMap_ST.zw;
    o.uv1 = input.uv1;
    return o;
}

// SI1_655/08ed673f 与旧 SharedEnvironment/GBufferFormula01 的同一环境模型。
// UV混合、遮罩重映射、镜面强度和法线解码顺序保留源公式，仅参数改为语义名字。
EFGBufferOutput EFSourceEnvironmentGBuffer(EFVaryings input, bool frontFace, float2 motion)
{
    float2 baseUV = lerp(input.uv, input.uv1, _EnvironmentAlbedoUVWeight);
    baseUV = baseUV * _EnvironmentBaseUV_ST.xy + _EnvironmentBaseUV_ST.zw;
    float2 materialUV = lerp(input.uv, input.uv1, _EnvironmentMaterialUVWeight);
    materialUV = materialUV * _EnvironmentMaterialUV_ST.xy + _EnvironmentMaterialUV_ST.zw;
    float3 baseColor = SAMPLE_TEXTURE2D_BIAS(_BaseMap, sampler_BaseMap, baseUV, _SourceMipBias).rgb * _BaseColor.rgb;
    baseColor = saturate(baseColor * _EnvironmentBaseGain);
    float3 mask = SAMPLE_TEXTURE2D_BIAS(_EnvironmentMaskMap, sampler_EnvironmentMaskMap, materialUV, _SourceMipBias).rgb;
    float metallic = lerp(mask.r, _EnvironmentMetallicOverride, saturate(_EnvironmentMetallicOverrideWeight - 1));
    float roughness = lerp(_EnvironmentRoughnessRange.x, _EnvironmentRoughnessRange.y, mask.g);
    float occlusion = 1 + _Occlusion * (mask.b - 1);
    float specular = saturate(_EnvironmentSpecularBias + metallic * _EnvironmentSpecularMetallicWeight + roughness * _EnvironmentSpecularRoughnessWeight);
    specular = (specular * 0.95 + 0.05) * (1 - _EnvironmentReflectionMask);
    float4 packed = SAMPLE_TEXTURE2D_BIAS(_NormalMap, sampler_NormalMap, materialUV, _SourceMipBias + _EnvironmentNormalMipBias);
    float2 xy = float2(packed.r * packed.a, packed.g) * 2 - 1;
    float z = max(sqrt(1 - min(dot(xy, xy), 1)), 1e-16);
    xy *= _NormalScale;
    z *= frontFace ? 1 : (_BackFaceNormal > 0 ? -1 : 1);
    float3 bitangent = cross(input.normalWS, input.tangentWS.xyz) * (input.tangentWS.w > 0 ? 1 : -1);
    float3 normal = normalize(input.tangentWS.xyz * xy.x + bitangent * xy.y + input.normalWS * z);
    EFGBufferOutput o;
    o.target0 = float4(0,0,0,0.5);
    o.target1 = float4(lerp(EFEncodeMotion(motion), 0.5, _EnvironmentMotionDisabled), lerp(_EnvironmentLightingWeight, 1, _EnvironmentMotionDisabled), 0.7 * _EnvironmentMotionDisabled);
    o.target2 = float4(metallic, occlusion, specular, floor(_EnvironmentMaterialTag / 4) / 3);
    o.target3 = float4(EFEncodeNormal(normal), roughness, fmod(_EnvironmentMaterialTag, 4) / 3);
    o.target4 = float4(lerp(baseColor, _BaseColor.rgb, _EnvironmentBaseBlend), 0);
    return o;
}
EFSurface EFSampleSurface(EFVaryings input, bool frontFace)
{
    EFSurface s;
    float4 base = SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv) * _BaseColor;
    #if defined(EF_ALPHA_CLIP)
        clip(base.a - _Cutoff);
    #endif
    float3 normalTS = float3(0, 0, 1);
    #if defined(EF_NORMAL_MAP)
        float4 packed = SAMPLE_TEXTURE2D(_NormalMap, sampler_NormalMap, input.uv);
        normalTS.xy = (packed.xy * 2 - 1) * _NormalScale;
        normalTS.z = sqrt(saturate(1 - dot(normalTS.xy, normalTS.xy)));
    #endif
    float3 n = normalize(input.normalWS);
    float3 t = SafeNormalize(input.tangentWS.xyz - n * dot(n, input.tangentWS.xyz));
    float3 b = cross(n, t) * input.tangentWS.w;
    s.normalWS = normalize(t * normalTS.x + b * normalTS.y + n * normalTS.z) * (frontFace ? 1 : -1);
    float4 mask = 1;
    #if defined(EF_MASK_MAP)
        mask = SAMPLE_TEXTURE2D(_MaskMap, sampler_MaskMap, input.uv);
    #endif
    // 这些 RGB 通道仅定义新语义材质，原 ILM 必须由已证明的源公式读取。
    s.baseColor = base.rgb;
    s.alpha = base.a;
    s.metallic = saturate(_Metallic * mask.r);
    s.roughness = clamp(_Roughness * mask.g, 0.04, 1);
    s.occlusion = lerp(1, mask.b, _Occlusion);
    s.specular = _Specular;
    s.nprWeight = _NprWeight;
    s.emission = SAMPLE_TEXTURE2D(_EmissionMap, sampler_EmissionMap, input.uv).rgb * _EmissionColor.rgb;
    s.family = 0;
    #if defined(EF_HAIR)
        s.family = 1;
    #elif defined(EF_CLOTH)
        s.family = 2;
    #elif defined(EF_FACE)
        s.family = 3;
    #elif defined(EF_EYE)
        s.family = 4;
    #endif
    return s;
}
// SI-1 的角色 GBuffer 公共段，直接重组旧 GBufferSurface/SharedMaterial 算法。
// 488/502:479a1a25；520/585/599:b3ed3da6；538/553/568:f3ad6268；617:d2a926b5。
EFGBufferOutput EFSourceCharacterGBuffer(EFVaryings input, bool frontFace, float2 motion)
{
    #if defined(EF_SOURCE_COVERAGE)
        clip(SAMPLE_TEXTURE2D_BIAS(_CoverageMap, sampler_CoverageMap, input.uv, _SourceMipBias).r - _Cutoff);
    #endif
    float3 color = SAMPLE_TEXTURE2D_BIAS(_BaseMap, sampler_BaseMap, input.uv, _SourceMipBias).rgb * _BaseColor.rgb;
    float3 normal = normalize(input.normalWS);
    #if defined(EF_NORMAL_MAP)
        float4 packed = SAMPLE_TEXTURE2D_BIAS(_NormalMap, sampler_NormalMap, input.uv, _SourceMipBias);
        // 源路径在解码XY前执行R*=A；BC5的A恒1，兼容旧RGBA法线。
        #if !defined(EF_SOURCE_COVERAGE)
            packed.r *= packed.a;
        #endif
        float2 xy = packed.xy * 2 - 1;
        // 源法线的Z在XY乘强度前重建，不能改成标准缩放后重建。
        float z = sqrt(1 - min(dot(xy, xy), 1));
        xy *= _NormalScale;
        float3 tangent = input.tangentWS.xyz;
        float3 bitangent = cross(input.normalWS, tangent) * input.tangentWS.w;
        normal = normalize(tangent * xy.x + bitangent * xy.y + input.normalWS * z);
    #endif
    normal = normalize(normal * (frontFace ? 1 : _BackFaceNormal * 2 - 1));
    #if defined(EF_SOURCE_VIEW_TINT)
        // 原cb3[12].x、cb3[13].rgb视角染色；Unity当前视线替代捕获view列。
        float3 view = normalize(_WorldSpaceCameraPos - input.positionWS);
        float fresnelTint = saturate((1 - (saturate(dot(normal, view)) * 0.85 + 0.15)) * _ViewTintStrength);
        color *= lerp(1, _ViewTintColor.rgb, fresnelTint);
    #endif
    EFGBufferOutput o;
    o.target0 = 0;
    o.target1 = float4(EFEncodeMotion(motion), 1, 0.4);
    // 这是原实例页cb[5].z解码结果，绝不是金属/遮蔽/高光。
    o.target2 = EFCharacterShadowPayload(_SourceInstancePayload, (int)_CharacterShadowIndex);
    o.target3 = float4(EFEncodeNormal(normal), 0, _SourceGBufferTag);
    o.target4 = float4(color, 1);
    return o;
}
#endif
