#ifndef ENDFIELD_PARALLAX_GLOW_INCLUDED
#define ENDFIELD_PARALLAX_GLOW_INCLUDED
// SI1_1143:309-378，水晶高度图R作视差射线，偏移后的R作冷色附加响应。
// 这不是环境Cube或捕获光照贴图；输入是静态材质图，视差由当前相机/切线基底生成。
float3 EFSourceParallaxGlow(EFVaryings input, EFSurface surface, bool frontFace)
{
    float3 geometricNormal = normalize(input.normalWS) * (frontFace ? 1 : 2*_BackFaceNormal-1);
    float3 normal = _ParallaxGlowParams.z > 0.5 ? surface.normalWS : geometricNormal;
    float normalLength = length(normal);
    float3 tangent = input.tangentWS.xyz / normalLength;
    float3 bitangent = cross(normal,input.tangentWS.xyz) * (input.tangentWS.w > 0 ? 1 : -1) / normalLength;
    normal /= normalLength;
    float3 view = normalize(_WorldSpaceCameraPos-input.positionWS);
    float3 viewTS = normalize(float3(dot(tangent,view),dot(bitangent,view),dot(normal,view)));
    float steps = min(20,_ParallaxGlowParams.x);
    float stepHeight = 1/steps;
    float2 ray = viewTS.xy / max(viewTS.z,0.001) * -_ParallaxGlowParams.y;
    float2 rayStep = ray*stepHeight;
    float2 offset = rayStep;
    float layerHeight = 1-stepHeight;
    float2 previousOffset = 0;
    float previousHeight = 0;
    float previousLayer = 1;
    float sampledHeight = 0;
    float2 baseUV = input.uv*_ParallaxGlowMap_ST.xy+_ParallaxGlowMap_ST.zw;
    // 原gradient取原始UV导数，不乘M14.xy；frame[26].y等于exp2(mipBias)。
    float2 derivativeX = ddx_coarse(input.uv)*exp2(_SourceMipBias);
    float2 derivativeY = ddy_coarse(input.uv)*exp2(_SourceMipBias);
    [loop] for (int stepIndex=0;stepIndex<steps+1;stepIndex++)
    {
        sampledHeight = SAMPLE_TEXTURE2D_GRAD(_ParallaxGlowMap,sampler_ParallaxGlowMap,baseUV+offset,derivativeX,derivativeY).r;
        if (layerHeight<sampledHeight) break;
        previousOffset=offset;
        previousHeight=sampledHeight;
        previousLayer=layerHeight;
        offset+=rayStep;
        layerHeight-=stepHeight;
    }
    float interpolation = (previousHeight-previousLayer)/(layerHeight+previousHeight-sampledHeight-previousLayer);
    float2 finalUV = baseUV+previousOffset+rayStep*interpolation;
    // dest=r8.w、resource swizzle=yzwx，写入w的是原纹理R。
    float response = SAMPLE_TEXTURE2D_BIAS(_ParallaxGlowMap,sampler_ParallaxGlowMap,finalUV,_SourceMipBias).r;
    float baseAlpha = SAMPLE_TEXTURE2D_BIAS(_BaseMap,sampler_BaseMap,input.uv,_SourceMipBias).a*_BaseColor.a;
    // 源1143:1356-1359；独立于源t20普通Emission和环境镜面项。
    return response*_ParallaxGlowColor.rgb*baseAlpha;
}
#endif
