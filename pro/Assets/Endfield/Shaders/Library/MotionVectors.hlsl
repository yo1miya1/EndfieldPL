#ifndef ENDFIELD_MOTION_VECTORS_INCLUDED
#define ENDFIELD_MOTION_VECTORS_INCLUDED
#include "Surface.hlsl"

// Unity ObjectMotionVectors的输入约定：蒙皮旧顶点在TEXCOORD4，普通网格使用当前顶点。
struct EFMotionAttributes
{
    float3 positionOS : POSITION;
    float3 previousPositionOS : TEXCOORD4;
    float2 uv : TEXCOORD0;
};
struct EFMotionVaryings
{
    float4 positionCS : SV_POSITION;
    float4 currentClip : TEXCOORD0;
    float4 previousClip : TEXCOORD1;
    float2 uv : TEXCOORD2;
};
EFMotionVaryings EFMotionVertex(EFMotionAttributes input)
{
    EFMotionVaryings output;
    float4 world = mul(unity_ObjectToWorld, float4(input.positionOS, 1));
    output.positionCS = mul(unity_MatrixVP, world);
    output.currentClip = mul(_EndfieldNonJitteredViewProjection, world);
    float3 previousPosition = unity_MotionVectorsParams.x == 1 ? input.previousPositionOS : input.positionOS;
    float4 previousWorld = mul(unity_MatrixPreviousM, float4(previousPosition, 1));
    output.previousClip = mul(_TemporalPreviousViewProjection, previousWorld);
    output.uv = input.uv * _BaseMap_ST.xy + _BaseMap_ST.zw;
    return output;
}
float4 EFMotionFragment(EFMotionVaryings input) : SV_Target
{
    #if defined(EF_ALPHA_CLIP)
        clip(SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv).a * _BaseColor.a - _Cutoff);
    #endif
    #if defined(EF_SOURCE_COVERAGE)
        clip(SAMPLE_TEXTURE2D_BIAS(_CoverageMap, sampler_CoverageMap, input.uv, _SourceMipBias).r - _Cutoff);
    #endif
    // ForceNoMotion的Unity语义；jitter不进入velocity，静止画面仍可积累不同子像素覆盖。
    if (unity_MotionVectorsParams.y == 0) return 0;
    float2 velocity = (input.previousClip.xy / input.previousClip.w - input.currentClip.xy / input.currentClip.w) * .5;
    #if UNITY_UV_STARTS_AT_TOP
        velocity.y = -velocity.y;
    #endif
    return float4(velocity, 0, 1);
}
#endif
