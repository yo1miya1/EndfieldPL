#ifndef ENDFIELD_BRDF_INCLUDED
#define ENDFIELD_BRDF_INCLUDED
#include "GBuffer.hlsl"

// 可读的 GGX/Schlick 重构基线，尚不是 SI-1 源直接光公式的等价证明。
float3 EFFresnel(float3 f0, float cosine) { return f0 + (1 - f0) * EFPow5(1 - saturate(cosine)); }
float3 EFEvaluateBRDF(EFSurface s, float3 view, float3 light, float3 radiance, float shadow)
{
    float3 halfVector = SafeNormalize(view + light);
    float nl = saturate(dot(s.normalWS, light));
    float nv = max(saturate(dot(s.normalWS, view)), 0.001);
    float nh = saturate(dot(s.normalWS, halfVector));
    float vh = saturate(dot(view, halfVector));
    float a = max(s.roughness * s.roughness, 0.002);
    float a2 = a * a;
    float d = a2 / max(PI * EFSquare(nh * nh * (a2 - 1) + 1), 1e-5);
    float k = EFSquare(s.roughness + 1) / 8;
    float visibility = rcp(max((nv * (1 - k) + k) * (nl * (1 - k) + k) * 4, 1e-4));
    float3 f0 = lerp(s.specular.xxx * 0.08, s.baseColor, s.metallic);
    float3 fresnel = EFFresnel(f0, vh);
    float3 diffuse = (1 - fresnel) * (1 - s.metallic) * s.baseColor / PI;
    float3 specular = d * visibility * fresnel;
    // NPR 平滑明暗分区；家族分支是明确的诊断实现，等待源证据替换。
    float halfLambert = dot(s.normalWS, light) * 0.5 + 0.5;
    float band = smoothstep(0.45, 0.55, halfLambert * shadow);
    float3 nprDiffuse = s.baseColor * lerp(0.25, 1, band) / PI;
    float nprSpecular = smoothstep(0.65, 0.8, nh) * s.specular;
    if (s.family == 1) nprSpecular *= smoothstep(0.75, 0.9, nh); // 头发高光暂以较窄高光瓣诊断。
    if (s.family == 3) nprSpecular *= 0.15; // 面部暂抑制高光，不能替代脸部 SDF。
    if (s.family == 4) nprSpecular *= 2; // 眼睛保持高光。
    float3 pbr = (diffuse + specular) * nl * shadow;
    float3 npr = nprDiffuse + nprSpecular * shadow;
    return lerp(pbr, npr, s.nprWeight) * radiance;
}
#endif
