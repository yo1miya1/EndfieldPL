#ifndef ENDFIELD_ENVIRONMENT_REFLECTION_INCLUDED
#define ENDFIELD_ENVIRONMENT_REFLECTION_INCLUDED
#include "Packages/com.unity.render-pipelines.core/ShaderLibrary/EntityLighting.hlsl"

TEXTURECUBE(unity_SpecCube0); SAMPLER(samplerunity_SpecCube0);

// SI1_1122:1267-1297，源环境BRDF的两个有理多项式。
// 这里的roughness是感知粗糙度；不能换成标准split-sum LUT或Unity默认拟合。
float2 EFSourceEnvironmentBRDF(float nv, float roughness)
{
    float nv2 = nv * nv;
    float nv3 = nv2 * nv;
    float r2 = roughness * roughness;
    float r6 = r2 * r2 * r2;
    float numeratorA = 3.32707 * nv + 0.0365464 + (-9.04756 * nv + 9.0632) * r2;
    float denominatorA = 3.59685 * nv2 - 1.36772 * nv3 + 1
        + (-16.3174 * nv2 + 9.04401 + 9.22949 * nv3) * r2
        + (5.56589 + 19.788601 * nv2 - 20.212299 * nv3) * r6;
    float numeratorB = -1.28514 * nv + 0.99044 + (1.29678 - 0.755907 * nv) * r2;
    float denominatorB = 2.92338 * nv + 59.4188 * nv3 + 1
        + (20.3225 - 27.030199 * nv + 222.591995 * nv3) * r2
        + (626.130005 * nv + 316.627014 * nv3 + 121.563004) * r6;
    return float2(numeratorA / denominatorA, numeratorB / denominatorB);
}

float3 EFUnityProbeRadiance(float3 reflectionDirection, float3 positionWS, float roughness)
{
    // ReflectionProbe.boxProjection直接使用Unity逐Renderer常量，动态相机/物体仍可移动。
    if (unity_SpecCube0_ProbePosition.w > 0)
    {
        float3 intersectionDistance = ((reflectionDirection > 0 ? unity_SpecCube0_BoxMax.xyz : unity_SpecCube0_BoxMin.xyz) - positionWS) / reflectionDirection;
        float distanceToBox = min(intersectionDistance.x, min(intersectionDistance.y, intersectionDistance.z));
        reflectionDirection = positionWS - unity_SpecCube0_ProbePosition.xyz + reflectionDirection * distanceToBox;
    }
    // 源1122:1316-1320，保留原预卷积mip映射，不重复进行Unity粗糙度重映射。
    float mip = 1.2 * log2(max(roughness, 0.001)) + 5;
    float4 encoded = SAMPLE_TEXTURECUBE_LOD(unity_SpecCube0, samplerunity_SpecCube0, reflectionDirection, mip);
    return DecodeHDREnvironment(encoded, unity_SpecCube0_HDR);
}

float3 EFSourceEnvironmentSpecularWithNormal(float3 normalWS, float3 reflectionNormalWS, float3 view, float3 positionWS, float roughness, float3 f0)
{
    float2 brdf = EFSourceEnvironmentBRDF(saturate(dot(normalWS, view)), roughness);
    float3 reflectionDirection = reflect(-view, reflectionNormalWS);
    // 源G126=(cos-like,sin-like)采用(x'=z*x+x*y,z'=z*y-x*x)约定。
    // 当前捕获(0,1)为恒等；离线Cubemap已转换至Unity世界基底。
    reflectionDirection.xz = float2(dot(reflectionDirection.zx, _SourceEnvironmentRotation.xy),
        reflectionDirection.z * _SourceEnvironmentRotation.y - reflectionDirection.x * _SourceEnvironmentRotation.x);
    float3 radiance = EFUnityProbeRadiance(reflectionDirection, positionWS, roughness);
    float totalEnergy = brdf.x + brdf.y;
    // 源1122:1321-1325，多次散射能量补偿；非任意增亮参数。
    return radiance * (f0 * brdf.x + brdf.y) * (1 + f0 * (1 - totalEnergy) / totalEnergy);
}
float3 EFSourceEnvironmentSpecular(float3 normalWS, float3 view, float3 positionWS, float roughness, float3 f0)
{
    return EFSourceEnvironmentSpecularWithNormal(normalWS,normalWS,view,positionWS,roughness,f0);
}
#endif
