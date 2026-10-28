#ifndef ENDFIELD_SOURCE_EFFECT_INCLUDED
#define ENDFIELD_SOURCE_EFFECT_INCLUDED
#include "Surface.hlsl"
float _EndfieldSceneExposure;

// SI1_1190/977aae30 源效果片元：本帧扭曲、溶解和深度淡出开关为零。
// COLOR为stride=0的常量VB，所以离线读取为_EffectVertexColor，不伪造顶点流。
float4 EFSourceEffect(EFVaryings input)
{
    float4 vertexColor = lerp(_EffectVertexColor, 1, _EffectIgnoreVertexColor);
    float4 color = vertexColor * _EffectColor * float4(_EffectColorIntensity.xxx, _EffectAlphaIntensity);
    float4 sampled = SAMPLE_TEXTURE2D_BIAS(_BaseMap, sampler_BaseMap, input.uv, _SourceMipBias + trunc(_EffectMipBias));
    sampled = lerp(sampled, float4(1,1,1,sampled.r), _EffectMonochromeWeight);
    color *= sampled * (1 - _EffectInvisibleWeight);
    if (_EffectDissolveEnabled != 0)
    {
        float influence = _EffectDissolveHeight * _EffectDissolveProfile.w;
        float mask = lerp(1, 1 - _EffectDissolveMask, influence);
        // 可扩展的生成UV高度来自当前对象UV1；本帧该分支不执行。
        float edge = mask * ((input.uv1.x + _EffectDissolveProfile.y) * 2.02 - 0.01) - 1;
        float alpha = saturate(-edge * _EffectDissolveProfile.x);
        float edgeColor = saturate((edge + _EffectDissolveProfile.z) * _EffectDissolveProfile.x);
        color.rgb = lerp(color.rgb, _EffectDissolveColor.rgb * _EffectColorIntensity, edgeColor * edgeColor);
        color.a *= alpha;
    }
    color.rgb += max(color.rgb - _EffectBloomThreshold, 0) * _EffectBloomBoost;
    color.rgb *= lerp(1, _EndfieldSceneExposure, _EffectPreExposureWeight);
    color.rgb = clamp(color.rgb, 0, 1000);
    float depthFade = 1;
    if (_EffectDepthFadeEnabled != 0)
    {
        float distance = abs(mul(unity_MatrixV, float4(input.positionWS, 1)).z);
        float nearFade = saturate((distance - _EffectDepthRanges.x) / (_EffectDepthRanges.y - _EffectDepthRanges.x));
        float farFade = saturate((distance - _EffectDepthRanges.z) / (_EffectDepthRanges.w - _EffectDepthRanges.z));
        depthFade = nearFade * farFade;
    }
    float alpha = saturate(depthFade * color.a) * _EffectInstanceOpacity * _EffectOpacity;
    float3 premultiplied = color.rgb * alpha;
    if (_EffectAlphaMode == 2) premultiplied += 1 - alpha;
    float luminance = dot(premultiplied, float3(0.212673,0.715152,0.072175));
    float3 response = lerp(luminance.xxx, premultiplied, _EffectColorResponse.w) * _EffectColorResponse.rgb;
    return float4(lerp(premultiplied, response, _EffectColorResponseWeight), alpha);
}
#endif
