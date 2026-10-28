#ifndef ENDFIELD_SOURCE_EYE_INCLUDED
#define ENDFIELD_SOURCE_EYE_INCLUDED

// SI1_1061 PS32-61。源VS只在顶点归一化N/T，PS按N长度同尺度处理T/B/N。
// 保留原插值基底，不将三个轴独立归一化；本次seam的输入根因是导出的N/T方向和w错误。
float2 EFSourceEyeParallaxUV(EFVaryings input, out float2 eyeUV, out float outsideIris)
{
    eyeUV = frac(input.uv);
    float2 centered = eyeUV-0.5;
    float radiusSquared = dot(centered,centered);
    outsideIris = radiusSquared>=0.25 ? 1 : 0;
    float inverseNormalLength = rsqrt(dot(input.normalWS,input.normalWS));
    float3 parallaxTangent = input.tangentWS.xyz*inverseNormalLength;
    float3 parallaxBitangent = cross(input.normalWS,input.tangentWS.xyz)*(input.tangentWS.w>0 ? 1 : -1)*inverseNormalLength;
    float3 parallaxNormal = input.normalWS*inverseNormalLength;
    float3 view = normalize(_WorldSpaceCameraPos-input.positionWS);
    float3 tangentView = normalize(float3(dot(parallaxTangent,view),dot(parallaxBitangent,view),dot(parallaxNormal,view)));
    float weight = saturate((radiusSquared-0.25)*-5);
    weight = weight*weight*(3-2*weight);
    return input.uv-tangentView.xy*_EyeParallax*float2(1,0.25)*weight;
}

void EFSourceEyeNormals(EFVaryings input, float2 eyeUV, float outsideIris, out float3 irisNormalWS, out float3 corneaNormalWS)
{
    // SI1_1061 PS80-95/452-460。此处也保留插值基底，不能独立归一化T/N后重建。
    float2 circle = eyeUV*2-1;
    float3 cornea = float3(circle*-_EyeCurvature,sqrt(1-min(dot(circle,circle),1)));
    float3 iris = lerp(cornea*float3(-0.125,-0.125,1),float3(0,0,1),outsideIris);
    float3 bitangent = cross(input.normalWS,input.tangentWS.xyz)*input.tangentWS.w;
    irisNormalWS = normalize(input.tangentWS.xyz*iris.x+bitangent*iris.y+input.normalWS*iris.z);
    corneaNormalWS = input.tangentWS.xyz*cornea.x+bitangent*cornea.y+input.normalWS*cornea.z;
}
#endif
