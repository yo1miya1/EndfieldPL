#ifndef ENDFIELD_SHADOWS_INCLUDED
#define ENDFIELD_SHADOWS_INCLUDED
#include "Coordinates.hlsl"
#include "Packages/com.unity.render-pipelines.core/ShaderLibrary/Shadow/ShadowSamplingTent.hlsl"
TEXTURE2D_SHADOW(_MainLightShadowmapTexture);
SAMPLER_CMP(sampler_LinearClampCompare);
float4x4 _MainLightWorldToShadow[4];
float4 _MainLightShadowCascadeSpheres[4];
float4 _MainLightShadowParams;
float _MainLightShadowFilter;
TEXTURE2D_SHADOW(_AdditionalLightShadowmapTexture);
float4x4 _AdditionalLightWorldToShadow[192];
float4 _AdditionalLightShadowRects[192];
float4 _AdditionalLightShadowParams[32];
float4 _AdditionalShadowAtlasSize;

float4 EFMainShadowCoordinates(float3 positionWS)
{
    int cascade = -1;
    [unroll] for (int i = 0; i < 4; i++)
    {
        float3 delta = positionWS - _MainLightShadowCascadeSpheres[i].xyz;
        if (i < (int)_MainLightShadowParams.y && cascade < 0 && dot(delta, delta) < _MainLightShadowCascadeSpheres[i].w) cascade = i;
    }
    if (cascade < 0) return float4(0,0,0,0);
    float4 p = mul(_MainLightWorldToShadow[cascade], float4(positionWS, 1));
    float3 uvz = p.xyz / p.w;
    float columns = _MainLightShadowParams.y <= 1 ? 1 : 2;
    float2 minimum = float2(cascade % (int)columns, cascade / (int)columns) / columns;
    bool inside = all(uvz.xy >= minimum) && all(uvz.xy <= minimum + 1 / columns) && uvz.z >= 0 && uvz.z <= 1;
    return float4(uvz, inside ? cascade + 1 : 0);
}

// 硬阴影使用单次原生比较；软阴影复用Unity Core的5x5 Tent（9次双线性比较）。
float EFMainShadow(float3 positionWS)
{
    if (_MainLightShadowParams.x <= 0) return 1;
    float4 coordinates = EFMainShadowCoordinates(positionWS);
    if (coordinates.w == 0) return 1;
    float3 uvz = coordinates.xyz;
    int cascade = (int)coordinates.w - 1;
    int columns = _MainLightShadowParams.y <= 1 ? 1 : 2;
    float2 minimum = float2(cascade % columns, cascade / columns) / columns + _MainLightShadowParams.z * .5;
    float2 maximum = minimum + 1.0 / columns - _MainLightShadowParams.z;
    float shadow;
    if (_MainLightShadowFilter < 0.5)
        shadow = SAMPLE_TEXTURE2D_SHADOW(_MainLightShadowmapTexture, sampler_LinearClampCompare, uvz);
    else
    {
        real weights[9];
        real2 sampleUVs[9];
        float texel = _MainLightShadowParams.z;
        SampleShadow_ComputeSamples_Tent_5x5(float4(texel,texel,1/texel,1/texel), uvz.xy, weights, sampleUVs);
        shadow = 0;
        [unroll] for (int tap = 0; tap < 9; tap++)
            shadow += weights[tap] * SAMPLE_TEXTURE2D_SHADOW(_MainLightShadowmapTexture, sampler_LinearClampCompare, float3(clamp(sampleUVs[tap], minimum, maximum),uvz.z));
    }
    return lerp(1, shadow, _MainLightShadowParams.x);
}

float EFAdditionalShadow(int lightIndex, float3 positionWS, float3 lightPositionWS)
{
    float4 parameters = _AdditionalLightShadowParams[lightIndex];
    if (parameters.x <= 0) return 1;
    int slice = (int)parameters.z;
    // Unity CubemapFace顺序；选从点光射向receiver的主轴面。
    if (parameters.w > .5) slice += (int)CubeMapFaceID(positionWS - lightPositionWS);
    float4 projected = mul(_AdditionalLightWorldToShadow[slice], float4(positionWS, 1));
    if (projected.w <= 0) return 1;
    float3 uvz = projected.xyz / projected.w;
    float4 rectangle = _AdditionalLightShadowRects[slice];
    if (any(uvz.xy < rectangle.xy) || any(uvz.xy > rectangle.zw) || uvz.z < 0 || uvz.z > 1) return 1;
    float shadow;
    if (parameters.y < .5)
        shadow = SAMPLE_TEXTURE2D_SHADOW(_AdditionalLightShadowmapTexture, sampler_LinearClampCompare, uvz);
    else
    {
        real weights[9]; real2 sampleUVs[9];
        SampleShadow_ComputeSamples_Tent_5x5(_AdditionalShadowAtlasSize, uvz.xy, weights, sampleUVs);
        shadow = 0;
        [unroll] for (int tap = 0; tap < 9; tap++)
            shadow += weights[tap] * SAMPLE_TEXTURE2D_SHADOW(_AdditionalLightShadowmapTexture, sampler_LinearClampCompare,
                float3(clamp(sampleUVs[tap], rectangle.xy, rectangle.zw), uvz.z));
    }
    return lerp(1, shadow, parameters.x);
}
#endif
