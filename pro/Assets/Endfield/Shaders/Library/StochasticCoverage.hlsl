#ifndef ENDFIELD_STOCHASTIC_COVERAGE_INCLUDED
#define ENDFIELD_STOCHASTIC_COVERAGE_INCLUDED
// 源424的覆盖率规则；纹理/UV/像素坐标均由当前几何与阴影相机提供。
void EFStochasticCoverageClip(TEXTURE2D_PARAM(alphaMap, alphaSampler), float2 uv, float2 pixel, float opacity, float mipBias)
{
    float coverage = sqrt(SAMPLE_TEXTURE2D_BIAS(alphaMap, alphaSampler, uv, mipBias).a * opacity);
    float noise = frac(dot(pixel, float2(0.06711056,0.00583715)));
    noise = frac(noise * 52.9829189);
    noise = coverage >= 0 ? noise : -noise;
    clip(coverage - noise);
}
#endif
