#ifndef ENDFIELD_SOURCE_GROUND_INCLUDED
#define ENDFIELD_SOURCE_GROUND_INCLUDED
// 旧成熟SharedEnvironment/GBufferFormula02：只有运动/覆盖响应读取底图与距离场，
// RT4本身写材质底色。实际显示色由独立台面Forward计算，不将后者提前塞进GBuffer。
EFGBufferOutput EFSourceGroundGBuffer(EFVaryings input, float2 motion)
{
    float viewDepth = abs(mul(unity_MatrixV, float4(input.positionWS,1)).z);
    float transition = saturate((viewDepth - _GroundDistanceParameters.x)
        / (_GroundDistanceParameters.y - _GroundDistanceParameters.x));
    float4 pattern = SAMPLE_TEXTURE2D_BIAS(_CoverageMap,sampler_CoverageMap,
        input.uv * _GroundPatternUV_ST.xy + _GroundPatternUV_ST.zw,_SourceMipBias);
    float distanceValue = 0.5-pattern.r;
    float normalizedDistance = distanceValue / length(float2(ddx_coarse(distanceValue),ddy_coarse(distanceValue)));
    float coverage = saturate(0.5-lerp(distanceValue,normalizedDistance,transition));
    float4 baseSample = SAMPLE_TEXTURE2D_BIAS(_BaseMap,sampler_BaseMap,
        input.uv * _GroundBaseUV_ST.xy + _GroundBaseUV_ST.zw,_SourceMipBias) * _BaseColor;
    float layer = saturate((baseSample.a * _GroundCoverageParameters.y + pattern.a) * _GroundPatternColor.a);
    float3 displayed = _GroundPatternColor.rgb * coverage * layer * pattern.a
        + baseSample.rgb * _GroundColorGain.y * (1+_GroundColorGain.x*(_GroundColorGain.z-1));
    float alpha = baseSample.a * _GroundCoverageParameters.y;
    float response = saturate(10*max(dot(displayed,float3(.212672904,.715152204,.0721750036))*alpha,alpha));
    EFGBufferOutput output;
    output.target0 = float4(0,0,0,.5);
    output.target1 = float4(EFEncodeMotion(motion)*saturate(_GroundDistanceParameters.z+1-_GroundCoverageParameters.w),
        1,_GroundCoverageParameters.z*_GroundCoverageParameters.w*(response>.5 ? 1:0));
    output.target2 = float4(0,1,0,0);
    output.target3 = float4(.5,.5,1,0);
    output.target4 = float4(_BaseColor.rgb,0);
    return output;
}
#endif
