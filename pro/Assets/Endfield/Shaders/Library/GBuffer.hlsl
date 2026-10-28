#ifndef ENDFIELD_GBUFFER_INCLUDED
#define ENDFIELD_GBUFFER_INCLUDED
#include "Coordinates.hlsl"

// 五附件的格式沿用源管线；标记位和材质字段仍需逐 SI-1 家族对照。
// 此语义接口避免把原 cbN_vM 寄存器泄露给 Unity 材质用户。
struct EFSurface
{
    float3 baseColor;
    float3 normalWS;
    float3 emission;
    float metallic;
    float roughness;
    float occlusion;
    float specular;
    float nprWeight;
    float family;
    float alpha;
};
struct EFGBufferOutput
{
    float4 target0 : SV_Target0;
    float4 target1 : SV_Target1;
    float4 target2 : SV_Target2;
    float4 target3 : SV_Target3;
    float4 target4 : SV_Target4;
};
EFGBufferOutput EFEncodeGBuffer(EFSurface s, float2 motion)
{
    EFGBufferOutput o;
    o.target0 = float4(s.emission, 0);
    o.target1 = float4(EFEncodeMotion(motion), s.nprWeight, 0);
    o.target2 = float4(s.metallic, s.occlusion, s.specular, floor(s.family / 4) / 3);
    o.target3 = float4(EFEncodeNormal(s.normalWS), s.roughness, fmod(s.family, 4) / 3);
    o.target4 = float4(s.baseColor, s.alpha);
    return o;
}
EFSurface EFDecodeGBuffer(float4 g0, float4 g1, float4 g2, float4 g3, float4 g4)
{
    EFSurface s;
    s.emission = g0.rgb;
    s.baseColor = g4.rgb;
    s.normalWS = EFDecodeNormal(g3.xy);
    s.metallic = g2.x;
    s.occlusion = g2.y;
    s.specular = g2.z;
    s.roughness = max(g3.z, 0.04);
    s.nprWeight = g1.z;
    s.family = round(g2.w * 3) * 4 + round(g3.w * 3);
    s.alpha = g4.a;
    return s;
}
#endif
