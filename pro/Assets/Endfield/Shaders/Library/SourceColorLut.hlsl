// 复用旧工程已经完成的 LUT 算法，外部接口改为语义参数；不上传任何原始常量页。
// 白平衡 -> 分离色调 -> 通道混合 -> SMH/LGG -> HSV/曲线 -> 原显示映射。
// 原算法保留单赋值中间量，便于逐项对照；控制字只存在函数内部。
// 来源：EndfieldRendering/.../Raster/ColorLookupTable.hlsl（已验证旧实现）。
#ifndef ENDFIELD_SOURCE_COLOR_LUT_INCLUDED
#define ENDFIELD_SOURCE_COLOR_LUT_INCLUDED
#include "Coordinates.hlsl"
float4 _ColorLutGeneratorParams;
float4 _ColorLutWhiteBalance;
float4 _ColorLutFilter;
float4 _ColorLutMixerRed;
float4 _ColorLutMixerGreen;
float4 _ColorLutMixerBlue;
float4 _ColorLutHueSaturationContrast;
float4 _ColorLutLift;
float4 _ColorLutGamma;
float4 _ColorLutGain;
float4 _ColorLutShadows;
float4 _ColorLutMidtones;
float4 _ColorLutHighlights;
float4 _ColorLutRanges;
float4 _ColorLutSplitShadows;
float4 _ColorLutSplitHighlights;
Texture2D<float4> _EF_LutCurve0;
Texture2D<float4> _EF_LutCurve1;
Texture2D<float4> _EF_LutCurve2;
Texture2D<float4> _EF_LutCurve3;
Texture2D<float4> _EF_LutCurve4;
Texture2D<float4> _EF_LutCurve5;
Texture2D<float4> _EF_LutCurve6;
Texture2D<float4> _EF_LutCurve7;
SamplerState sampler_EFLut_linear_clamp;
void EFLutPS(float4 _input0 : SV_Position0, float2 _input1 : TEXCOORD0, out float4 _output0 : SV_Target0)
{
    // Mutable state only carries values across original control-flow edges.
    uint4 controlWords0 = 0u;
    uint4 controlWords1 = 0u;
    uint4 controlWords2 = 0u;
    uint4 controlWords3 = 0u;
    uint4 controlWords4 = 0u;
    uint4 controlWords5 = 0u;
    uint4 v0 = 0u;
    uint4 v1 = 0u;
    uint4 o0 = 0u;
    // 把插值输入写入原寄存器载体；浮点值按位装入uint，整数及正反面掩码保留原类型。
    v0.xyzw = asuint(_input0);
    v1.xy = asuint(_input1);
    float2 floatValue0 =
        (float2(asfloat(v1.x), asfloat(v1.y)) + float2((-asfloat(asuint(_ColorLutGeneratorParams).y)), (-asfloat(asuint(_ColorLutGeneratorParams).z))));
    float floatValue1 = (floatValue0.x * asfloat(asuint(_ColorLutGeneratorParams).x));
    float floatValue2 = frac(floatValue1);
    float quotientValue3 = (floatValue2 / asfloat(asuint(_ColorLutGeneratorParams).x));
    float floatValue4 = (floatValue0.x + (-quotientValue3));
    float3 floatValue5 = mad(float3(floatValue2, floatValue0.y, floatValue4),
                             float3(asfloat(asuint(_ColorLutGeneratorParams).w), asfloat(asuint(_ColorLutGeneratorParams).w), asfloat(asuint(_ColorLutGeneratorParams).w)),
                             float3(asfloat(0xbec5a683u), asfloat(0xbec5a683u), asfloat(0xbec5a683u)));
    float3 floatValue6 = (float3(floatValue5.x, floatValue5.y, floatValue5.z) *
                          float3(asfloat(0x4159b00eu), asfloat(0x4159b00eu), asfloat(0x4159b00eu)));
    float3 exponentValue7 = exp2(float3(floatValue6.x, floatValue6.y, floatValue6.z));
    float3 floatValue8 = (float3(exponentValue7.x, exponentValue7.y, exponentValue7.z) +
                          float3(asfloat(0xbd449774u), asfloat(0xbd449774u), asfloat(0xbd449774u)));
    float3 floatValue9 = (float3(floatValue8.x, floatValue8.y, floatValue8.z) *
                          float3(asfloat(0x3e3851ebu), asfloat(0x3e3851ebu), asfloat(0x3e3851ebu)));
    float dotProduct10 = dot(float3(asfloat(0x3ec7e32au), asfloat(0x3f0cc8efu), asfloat(0x3c123fb3u)),
                             float3(floatValue9.x, floatValue9.y, floatValue9.z));
    float dotProduct11 = dot(float3(asfloat(0x3d911567u), asfloat(0x3f769271u), asfloat(0x3ab1f688u)),
                             float3(floatValue9.x, floatValue9.y, floatValue9.z));
    float dotProduct12 = dot(float3(asfloat(0x3cbd4d68u), asfloat(0x3e0317f0u), asfloat(0x3f6fadc1u)),
                             float3(floatValue9.x, floatValue9.y, floatValue9.z));
    float3 floatValue13 = (float3(dotProduct10, dotProduct11, dotProduct12) *
                           float3(asfloat(asuint(_ColorLutWhiteBalance).x), asfloat(asuint(_ColorLutWhiteBalance).y), asfloat(asuint(_ColorLutWhiteBalance).z)));
    float dotProduct14 = dot(float3(asfloat(0x4036f12cu), asfloat(0xbfd07c31u), asfloat(0xbccbe836u)),
                             float3(floatValue13.x, floatValue13.y, floatValue13.z));
    float dotProduct15 = dot(float3(asfloat(0xbe5739f3u), asfloat(0x3f943fe6u), asfloat(0x39aa0442u)),
                             float3(floatValue13.x, floatValue13.y, floatValue13.z));
    float dotProduct16 = dot(float3(asfloat(0xbd2b430fu), asfloat(0xbdf20297u), asfloat(0x3f88ca2eu)),
                             float3(floatValue13.x, floatValue13.y, floatValue13.z));
    float dotProduct17 = dot(float3(asfloat(0x3ee1207du), asfloat(0x3ec415b1u), asfloat(0x3e35974eu)),
                             float3(dotProduct14, dotProduct15, dotProduct16));
    float dotProduct18 = dot(float3(asfloat(0x3db7e506u), asfloat(0x3f503c7du), asfloat(0x3dc62af2u)),
                             float3(dotProduct14, dotProduct15, dotProduct16));
    float dotProduct19 = dot(float3(asfloat(0x3c8fb86fu), asfloat(0x3de4712eu), asfloat(0x3f5ee675u)),
                             float3(dotProduct14, dotProduct15, dotProduct16));
    float3 floatValue20 = max(float3(dotProduct17, dotProduct18, dotProduct19),
                              float3(asfloat(0x00000000u), asfloat(0x00000000u), asfloat(0x00000000u)));
    float3 floatValue21 = min(float3(floatValue20.x, floatValue20.y, floatValue20.z),
                              float3(asfloat(0x477fe000u), asfloat(0x477fe000u), asfloat(0x477fe000u)));
    float3 floatValue22 = mad(float3(floatValue21.x, floatValue21.y, floatValue21.z),
                              float3(asfloat(0x3f000000u), asfloat(0x3f000000u), asfloat(0x3f000000u)),
                              float3(asfloat(0x377ffff6u), asfloat(0x377ffff6u), asfloat(0x377ffff6u)));
    float3 logarithmValue23 = log2(float3(floatValue22.x, floatValue22.y, floatValue22.z));
    float3 floatValue24 = (float3(logarithmValue23.x, logarithmValue23.y, logarithmValue23.z) +
                           float3(asfloat(0x411b851fu), asfloat(0x411b851fu), asfloat(0x411b851fu)));
    float3 floatValue25 = (float3(floatValue24.x, floatValue24.y, floatValue24.z) *
                           float3(asfloat(0x3d69ca3au), asfloat(0x3d69ca3au), asfloat(0x3d69ca3au)));
    float3 logarithmValue26 = log2(float3(floatValue21.x, floatValue21.y, floatValue21.z));
    uint3 comparisonMask27 = uint3((floatValue21.x < asfloat(0x37fffffcu) ? 0xffffffffu : 0u),
                                   (floatValue21.y < asfloat(0x37fffffcu) ? 0xffffffffu : 0u),
                                   (floatValue21.z < asfloat(0x37fffffcu) ? 0xffffffffu : 0u));
    float3 floatValue28 = (float3(logarithmValue26.x, logarithmValue26.y, logarithmValue26.z) +
                           float3(asfloat(0x411b851fu), asfloat(0x411b851fu), asfloat(0x411b851fu)));
    float3 floatValue29 = (float3(floatValue28.x, floatValue28.y, floatValue28.z) *
                           float3(asfloat(0x3d69ca3au), asfloat(0x3d69ca3au), asfloat(0x3d69ca3au)));
    uint3 wordValue30 = uint3((comparisonMask27.x != 0u ? asuint(floatValue25.x) : asuint(floatValue29.x)),
                              (comparisonMask27.y != 0u ? asuint(floatValue25.y) : asuint(floatValue29.y)),
                              (comparisonMask27.z != 0u ? asuint(floatValue25.z) : asuint(floatValue29.z)));
    float3 floatValue31 = (float3(asfloat(wordValue30.x), asfloat(wordValue30.y), asfloat(wordValue30.z)) +
                           float3(asfloat(0xbed3c1dcu), asfloat(0xbed3c1dcu), asfloat(0xbed3c1dcu)));
    float3 floatValue32 = mad(float3(floatValue31.x, floatValue31.y, floatValue31.z),
                              float3(asfloat(asuint(_ColorLutHueSaturationContrast).z), asfloat(asuint(_ColorLutHueSaturationContrast).z), asfloat(asuint(_ColorLutHueSaturationContrast).z)),
                              float3(asfloat(0x3ed3c1dcu), asfloat(0x3ed3c1dcu), asfloat(0x3ed3c1dcu)));
    uint4 comparisonMask33 = uint4((floatValue32.x < asfloat(0xbe9a4d27u) ? 0xffffffffu : 0u),
                                   (floatValue32.x < asfloat(0x3fbbe74fu) ? 0xffffffffu : 0u),
                                   (floatValue32.y < asfloat(0xbe9a4d27u) ? 0xffffffffu : 0u),
                                   (floatValue32.y < asfloat(0x3fbbe74fu) ? 0xffffffffu : 0u));
    float3 floatValue34 = mad(float3(floatValue32.x, floatValue32.y, floatValue32.z),
                              float3(asfloat(0x418c28f6u), asfloat(0x418c28f6u), asfloat(0x418c28f6u)),
                              float3(asfloat(0xc11b851fu), asfloat(0xc11b851fu), asfloat(0xc11b851fu)));
    uint2 comparisonMask35 = uint2((floatValue32.z < asfloat(0xbe9a4d27u) ? 0xffffffffu : 0u),
                                   (floatValue32.z < asfloat(0x3fbbe74fu) ? 0xffffffffu : 0u));
    float3 exponentValue36 = exp2(float3(floatValue34.x, floatValue34.y, floatValue34.z));
    uint2 wordValue37 = uint2((comparisonMask33.y != 0u ? asuint(exponentValue36.x) : 0x477fe000u),
                              (comparisonMask33.w != 0u ? asuint(exponentValue36.y) : 0x477fe000u));
    float3 floatValue38 = (float3(exponentValue36.x, exponentValue36.y, exponentValue36.z) +
                           float3(asfloat(0xb7800000u), asfloat(0xb7800000u), asfloat(0xb7800000u)));
    uint wordValue39 = (comparisonMask35.y != 0u ? asuint(exponentValue36.z) : 0x477fe000u);
    float3 floatValue40 = (float3(floatValue38.x, floatValue38.y, floatValue38.z) +
                           float3(floatValue38.x, floatValue38.y, floatValue38.z));
    uint2 wordValue41 = uint2((comparisonMask33.x != 0u ? asuint(floatValue40.x) : wordValue37.x),
                              (comparisonMask33.z != 0u ? asuint(floatValue40.y) : wordValue37.y));
    uint wordValue42 = (comparisonMask35.x != 0u ? asuint(floatValue40.z) : wordValue39);
    float dotProduct43 = dot(float3(asfloat(0x3fb9c8c3u), asfloat(0xbe722fe0u), asfloat(0xbe5c163cu)),
                             float3(asfloat(wordValue41.x), asfloat(wordValue41.y), asfloat(wordValue42)));
    float dotProduct44 = dot(float3(asfloat(0xbd9cc83au), asfloat(0x3f968eb2u), asfloat(0xbdcc22e4u)),
                             float3(asfloat(wordValue41.x), asfloat(wordValue41.y), asfloat(wordValue42)));
    float dotProduct45 = dot(float3(asfloat(0x3c084074u), asfloat(0xbbc5abdbu), asfloat(0x3f7f6a56u)),
                             float3(asfloat(wordValue41.x), asfloat(wordValue41.y), asfloat(wordValue42)));
    float3 floatValue46 = (float3(dotProduct43, dotProduct44, dotProduct45) *
                           float3(asfloat(asuint(_ColorLutFilter).x), asfloat(asuint(_ColorLutFilter).y), asfloat(asuint(_ColorLutFilter).z)));
    float3 floatValue47 = max(float3(floatValue46.x, floatValue46.y, floatValue46.z),
                              float3(asfloat(0x00000000u), asfloat(0x00000000u), asfloat(0x00000000u)));
    float3 logarithmValue48 = log2(float3(floatValue47.x, floatValue47.y, floatValue47.z));
    float3 floatValue49 = (float3(logarithmValue48.x, logarithmValue48.y, logarithmValue48.z) *
                           float3(asfloat(0x3ee8ba2fu), asfloat(0x3ee8ba2fu), asfloat(0x3ee8ba2fu)));
    float3 exponentValue50 = exp2(float3(floatValue49.x, floatValue49.y, floatValue49.z));
    float3 floatValue51 = (float3(exponentValue50.x, exponentValue50.y, exponentValue50.z) +
                           float3(exponentValue50.x, exponentValue50.y, exponentValue50.z));
    float3 floatValue52 = (float3(exponentValue50.x, exponentValue50.y, exponentValue50.z) *
                           float3(exponentValue50.x, exponentValue50.y, exponentValue50.z));
    float3 floatValue53 = min(float3(exponentValue50.x, exponentValue50.y, exponentValue50.z),
                              float3(asfloat(0x3f800000u), asfloat(0x3f800000u), asfloat(0x3f800000u)));
    float3 squareRoot54 = sqrt(float3(exponentValue50.x, exponentValue50.y, exponentValue50.z));
    float dotProduct55 = dot(float3(floatValue53.x, floatValue53.y, floatValue53.z),
                             float3(asfloat(0x3e8b6199u), asfloat(0x3f2c90a3u), asfloat(0x3d5be985u)));
    float floatValue56 = saturate((dotProduct55 + asfloat(asuint(_ColorLutSplitShadows).w)));
    float floatValue57 = ((-floatValue56) + asfloat(0x3f800000u));
    float3 floatValue58 = (float3(asfloat(0xbf000000u), asfloat(0xbf000000u), asfloat(0xbf000000u)) +
                           float3(asfloat(asuint(_ColorLutSplitShadows).x), asfloat(asuint(_ColorLutSplitShadows).y), asfloat(asuint(_ColorLutSplitShadows).z)));
    float3 floatValue59 =
        mad(float3(floatValue57, floatValue57, floatValue57), float3(floatValue58.x, floatValue58.y, floatValue58.z),
            float3(asfloat(0x3f000000u), asfloat(0x3f000000u), asfloat(0x3f000000u)));
    float3 floatValue60 = mad(float3((-floatValue59.x), (-floatValue59.y), (-floatValue59.z)),
                              float3(asfloat(0x40000000u), asfloat(0x40000000u), asfloat(0x40000000u)),
                              float3(asfloat(0x3f800000u), asfloat(0x3f800000u), asfloat(0x3f800000u)));
    float3 floatValue61 = (float3(floatValue52.x, floatValue52.y, floatValue52.z) *
                           float3(floatValue60.x, floatValue60.y, floatValue60.z));
    float3 floatValue62 = mad(float3(floatValue51.x, floatValue51.y, floatValue51.z),
                              float3(floatValue59.x, floatValue59.y, floatValue59.z),
                              float3(floatValue61.x, floatValue61.y, floatValue61.z));
    uint3 comparisonMask63 = uint3((floatValue59.x >= asfloat(0x3f000000u) ? 0xffffffffu : 0u),
                                   (floatValue59.y >= asfloat(0x3f000000u) ? 0xffffffffu : 0u),
                                   (floatValue59.z >= asfloat(0x3f000000u) ? 0xffffffffu : 0u));
    uint3 wordValue64 = uint3((comparisonMask63.x != 0u ? 0x00000000u : 0x3f800000u),
                              (comparisonMask63.y != 0u ? 0x00000000u : 0x3f800000u),
                              (comparisonMask63.z != 0u ? 0x00000000u : 0x3f800000u));
    uint3 wordBits65 = (uint3(comparisonMask63.x, comparisonMask63.y, comparisonMask63.z) &
                        uint3(0x3f800000u, 0x3f800000u, 0x3f800000u));
    float3 floatValue66 = (float3(floatValue62.x, floatValue62.y, floatValue62.z) *
                           float3(asfloat(wordValue64.x), asfloat(wordValue64.y), asfloat(wordValue64.z)));
    float3 floatValue67 = (float3((-floatValue59.x), (-floatValue59.y), (-floatValue59.z)) +
                           float3(asfloat(0x3f800000u), asfloat(0x3f800000u), asfloat(0x3f800000u)));
    float3 floatValue68 = mad(float3(floatValue59.x, floatValue59.y, floatValue59.z),
                              float3(asfloat(0x40000000u), asfloat(0x40000000u), asfloat(0x40000000u)),
                              float3(asfloat(0xbf800000u), asfloat(0xbf800000u), asfloat(0xbf800000u)));
    float3 floatValue69 = (float3(floatValue51.x, floatValue51.y, floatValue51.z) *
                           float3(floatValue67.x, floatValue67.y, floatValue67.z));
    float3 floatValue70 = mad(float3(squareRoot54.x, squareRoot54.y, squareRoot54.z),
                              float3(floatValue68.x, floatValue68.y, floatValue68.z),
                              float3(floatValue69.x, floatValue69.y, floatValue69.z));
    float3 floatValue71 = mad(float3(floatValue70.x, floatValue70.y, floatValue70.z),
                              float3(asfloat(wordBits65.x), asfloat(wordBits65.y), asfloat(wordBits65.z)),
                              float3(floatValue66.x, floatValue66.y, floatValue66.z));
    float3 floatValue72 = (float3(floatValue71.x, floatValue71.y, floatValue71.z) +
                           float3(floatValue71.x, floatValue71.y, floatValue71.z));
    float3 floatValue73 = (float3(floatValue71.x, floatValue71.y, floatValue71.z) *
                           float3(floatValue71.x, floatValue71.y, floatValue71.z));
    float3 squareRoot74 = sqrt(float3(floatValue71.x, floatValue71.y, floatValue71.z));
    float3 floatValue75 = (float3(asfloat(0xbf000000u), asfloat(0xbf000000u), asfloat(0xbf000000u)) +
                           float3(asfloat(asuint(_ColorLutSplitHighlights).x), asfloat(asuint(_ColorLutSplitHighlights).y), asfloat(asuint(_ColorLutSplitHighlights).z)));
    float3 floatValue76 =
        mad(float3(floatValue56, floatValue56, floatValue56), float3(floatValue75.x, floatValue75.y, floatValue75.z),
            float3(asfloat(0x3f000000u), asfloat(0x3f000000u), asfloat(0x3f000000u)));
    float3 floatValue77 = mad(float3((-floatValue76.x), (-floatValue76.y), (-floatValue76.z)),
                              float3(asfloat(0x40000000u), asfloat(0x40000000u), asfloat(0x40000000u)),
                              float3(asfloat(0x3f800000u), asfloat(0x3f800000u), asfloat(0x3f800000u)));
    float3 floatValue78 = (float3(floatValue73.x, floatValue73.y, floatValue73.z) *
                           float3(floatValue77.x, floatValue77.y, floatValue77.z));
    float3 floatValue79 = mad(float3(floatValue72.x, floatValue72.y, floatValue72.z),
                              float3(floatValue76.x, floatValue76.y, floatValue76.z),
                              float3(floatValue78.x, floatValue78.y, floatValue78.z));
    uint3 comparisonMask80 = uint3((floatValue76.x >= asfloat(0x3f000000u) ? 0xffffffffu : 0u),
                                   (floatValue76.y >= asfloat(0x3f000000u) ? 0xffffffffu : 0u),
                                   (floatValue76.z >= asfloat(0x3f000000u) ? 0xffffffffu : 0u));
    uint3 wordValue81 = uint3((comparisonMask80.x != 0u ? 0x00000000u : 0x3f800000u),
                              (comparisonMask80.y != 0u ? 0x00000000u : 0x3f800000u),
                              (comparisonMask80.z != 0u ? 0x00000000u : 0x3f800000u));
    uint3 wordBits82 = (uint3(comparisonMask80.x, comparisonMask80.y, comparisonMask80.z) &
                        uint3(0x3f800000u, 0x3f800000u, 0x3f800000u));
    float3 floatValue83 = (float3(floatValue79.x, floatValue79.y, floatValue79.z) *
                           float3(asfloat(wordValue81.x), asfloat(wordValue81.y), asfloat(wordValue81.z)));
    float3 floatValue84 = (float3((-floatValue76.x), (-floatValue76.y), (-floatValue76.z)) +
                           float3(asfloat(0x3f800000u), asfloat(0x3f800000u), asfloat(0x3f800000u)));
    float3 floatValue85 = mad(float3(floatValue76.x, floatValue76.y, floatValue76.z),
                              float3(asfloat(0x40000000u), asfloat(0x40000000u), asfloat(0x40000000u)),
                              float3(asfloat(0xbf800000u), asfloat(0xbf800000u), asfloat(0xbf800000u)));
    float3 floatValue86 = (float3(floatValue72.x, floatValue72.y, floatValue72.z) *
                           float3(floatValue84.x, floatValue84.y, floatValue84.z));
    float3 floatValue87 = mad(float3(squareRoot74.x, squareRoot74.y, squareRoot74.z),
                              float3(floatValue85.x, floatValue85.y, floatValue85.z),
                              float3(floatValue86.x, floatValue86.y, floatValue86.z));
    float3 floatValue88 = mad(float3(floatValue87.x, floatValue87.y, floatValue87.z),
                              float3(asfloat(wordBits82.x), asfloat(wordBits82.y), asfloat(wordBits82.z)),
                              float3(floatValue83.x, floatValue83.y, floatValue83.z));
    float3 logarithmValue89 = log2(float3(abs(floatValue88.x), abs(floatValue88.y), abs(floatValue88.z)));
    float3 floatValue90 = (float3(logarithmValue89.x, logarithmValue89.y, logarithmValue89.z) *
                           float3(asfloat(0x400ccccdu), asfloat(0x400ccccdu), asfloat(0x400ccccdu)));
    float3 exponentValue91 = exp2(float3(floatValue90.x, floatValue90.y, floatValue90.z));
    float dotProduct92 = dot(float3(exponentValue91.x, exponentValue91.y, exponentValue91.z),
                             float3(asfloat(asuint(_ColorLutMixerRed).x), asfloat(asuint(_ColorLutMixerRed).y), asfloat(asuint(_ColorLutMixerRed).z)));
    float dotProduct93 = dot(float3(exponentValue91.x, exponentValue91.y, exponentValue91.z),
                             float3(asfloat(asuint(_ColorLutMixerGreen).x), asfloat(asuint(_ColorLutMixerGreen).y), asfloat(asuint(_ColorLutMixerGreen).z)));
    float dotProduct94 = dot(float3(exponentValue91.x, exponentValue91.y, exponentValue91.z),
                             float3(asfloat(asuint(_ColorLutMixerBlue).x), asfloat(asuint(_ColorLutMixerBlue).y), asfloat(asuint(_ColorLutMixerBlue).z)));
    float3 floatValue95 = (float3(dotProduct92, dotProduct93, dotProduct94) *
                           float3(asfloat(asuint(_ColorLutMidtones).x), asfloat(asuint(_ColorLutMidtones).y), asfloat(asuint(_ColorLutMidtones).z)));
    float dotProduct96 = dot(float3(dotProduct92, dotProduct93, dotProduct94),
                             float3(asfloat(0x3e8b6199u), asfloat(0x3f2c90a3u), asfloat(0x3d5be985u)));
    float2 floatValue97 =
        (float2(dotProduct96, dotProduct96) + float2((-asfloat(asuint(_ColorLutRanges).x)), (-asfloat(asuint(_ColorLutRanges).z))));
    float2 floatValue98 = (float2((-asfloat(asuint(_ColorLutRanges).x)), (-asfloat(asuint(_ColorLutRanges).z))) +
                           float2(asfloat(asuint(_ColorLutRanges).y), asfloat(asuint(_ColorLutRanges).w)));
    float2 quotientValue99 =
        (float2(asfloat(0x3f800000u), asfloat(0x3f800000u)) / float2(floatValue98.x, floatValue98.y));
    float2 floatValue100 =
        saturate((float2(quotientValue99.x, quotientValue99.y) * float2(floatValue97.x, floatValue97.y)));
    float2 floatValue101 =
        mad(float2(floatValue100.x, floatValue100.y), float2(asfloat(0xc0000000u), asfloat(0xc0000000u)),
            float2(asfloat(0x40400000u), asfloat(0x40400000u)));
    float2 floatValue102 = (float2(floatValue100.x, floatValue100.y) * float2(floatValue100.x, floatValue100.y));
    float floatValue103 = (floatValue102.y * floatValue101.y);
    float floatValue104 = mad(floatValue101.x, floatValue102.x, (-floatValue103));
    float floatValue105 = mad((-floatValue101.x), floatValue102.x, asfloat(0x3f800000u));
    float3 floatValue106 =
        (float3(floatValue95.x, floatValue95.y, floatValue95.z) * float3(floatValue104, floatValue104, floatValue104));
    float3 floatValue107 = (float3(dotProduct92, dotProduct93, dotProduct94) *
                            float3(asfloat(asuint(_ColorLutShadows).x), asfloat(asuint(_ColorLutShadows).y), asfloat(asuint(_ColorLutShadows).z)));
    float3 floatValue108 = (float3(dotProduct92, dotProduct93, dotProduct94) *
                            float3(asfloat(asuint(_ColorLutHighlights).x), asfloat(asuint(_ColorLutHighlights).y), asfloat(asuint(_ColorLutHighlights).z)));
    float3 floatValue109 = mad(float3(floatValue107.x, floatValue107.y, floatValue107.z),
                               float3(floatValue105, floatValue105, floatValue105),
                               float3(floatValue106.x, floatValue106.y, floatValue106.z));
    float3 floatValue110 = mad(float3(floatValue108.x, floatValue108.y, floatValue108.z),
                               float3(floatValue103, floatValue103, floatValue103),
                               float3(floatValue109.x, floatValue109.y, floatValue109.z));
    float3 floatValue111 = mad(float3(floatValue110.x, floatValue110.y, floatValue110.z),
                               float3(asfloat(asuint(_ColorLutGain).x), asfloat(asuint(_ColorLutGain).y), asfloat(asuint(_ColorLutGain).z)),
                               float3(asfloat(asuint(_ColorLutLift).x), asfloat(asuint(_ColorLutLift).y), asfloat(asuint(_ColorLutLift).z)));
    uint3 comparisonMask112 = uint3((asfloat(0x00000000u) < floatValue111.x ? 0xffffffffu : 0u),
                                    (asfloat(0x00000000u) < floatValue111.y ? 0xffffffffu : 0u),
                                    (asfloat(0x00000000u) < floatValue111.z ? 0xffffffffu : 0u));
    uint3 comparisonMask113 = uint3((floatValue111.x < asfloat(0x00000000u) ? 0xffffffffu : 0u),
                                    (floatValue111.y < asfloat(0x00000000u) ? 0xffffffffu : 0u),
                                    (floatValue111.z < asfloat(0x00000000u) ? 0xffffffffu : 0u));
    float3 logarithmValue114 = log2(float3(abs(floatValue111.x), abs(floatValue111.y), abs(floatValue111.z)));
    float3 floatValue115 = (float3(logarithmValue114.x, logarithmValue114.y, logarithmValue114.z) *
                            float3(asfloat(asuint(_ColorLutGamma).x), asfloat(asuint(_ColorLutGamma).y), asfloat(asuint(_ColorLutGamma).z)));
    float3 exponentValue116 = exp2(float3(floatValue115.x, floatValue115.y, floatValue115.z));
    uint3 wordValue117 =
        (int3((-asint(comparisonMask112.x)), (-asint(comparisonMask112.y)), (-asint(comparisonMask112.z))) +
         uint3(comparisonMask113.x, comparisonMask113.y, comparisonMask113.z));
    float3 floatValue118 = (float3)(int3(asint(wordValue117.x), asint(wordValue117.y), asint(wordValue117.z)));
    float3 floatValue119 = (float3(exponentValue116.x, exponentValue116.y, exponentValue116.z) *
                            float3(floatValue118.x, floatValue118.y, floatValue118.z));
    uint2 wordValue120 = uint2(asuint(floatValue119.z), asuint(floatValue119.y));
    float2 floatValue121 = mad(float2(floatValue118.y, floatValue118.z), float2(exponentValue116.y, exponentValue116.z),
                               float2((-asfloat(wordValue120.x)), (-asfloat(wordValue120.y))));
    uint comparisonMask122 = (asfloat(wordValue120.y) >= floatValue119.z ? 0xffffffffu : 0u);
    uint wordBits123 = (comparisonMask122 & 0x3f800000u);
    uint2 wordValue124 = uint2(0xbf800000u, 0x3f2aaaabu);
    uint2 wordValue125 = uint2(0x3f800000u, 0xbf800000u);
    float4 floatValue126 =
        mad(float4(asfloat(wordBits123), asfloat(wordBits123), asfloat(wordBits123), asfloat(wordBits123)),
            float4(floatValue121.x, floatValue121.y, asfloat(wordValue125.y), asfloat(wordValue125.x)),
            float4(asfloat(wordValue120.x), asfloat(wordValue120.y), asfloat(wordValue124.y), asfloat(wordValue124.x)));
    uint comparisonMask127 = (floatValue119.x >= floatValue126.x ? 0xffffffffu : 0u);
    uint wordBits128 = (comparisonMask127 & 0x3f800000u);
    uint wordValue129 = asuint(floatValue126.w);
    uint wordValue130 = asuint(floatValue119.x);
    float dotProduct131 = dot(float3(floatValue119.x, floatValue119.y, floatValue119.z),
                              float3(asfloat(0x3e59c6edu), asfloat(0x3f371437u), asfloat(0x3d93d07du)));
    uint3 wordValue132 = uint3(wordValue130, asuint(floatValue126.y), asuint(floatValue126.x));
    float4 floatValue133 =
        (float4((-floatValue126.x), (-floatValue126.y), (-floatValue126.z), (-asfloat(wordValue130))) +
         float4(asfloat(wordValue132.x), asfloat(wordValue132.y), asfloat(wordValue129), asfloat(wordValue132.z)));
    float4 floatValue134 =
        mad(float4(asfloat(wordBits128), asfloat(wordBits128), asfloat(wordBits128), asfloat(wordBits128)),
            float4(floatValue133.x, floatValue133.y, floatValue133.z, floatValue133.w),
            float4(floatValue126.x, floatValue126.y, floatValue126.z, asfloat(wordValue130)));
    float floatValue135 = min(floatValue134.y, floatValue134.w);
    float floatValue136 = (floatValue134.x + (-floatValue135));
    float floatValue137 = mad(floatValue136, asfloat(0x40c00000u), asfloat(0x38d1b717u));
    float floatValue138 = ((-floatValue134.y) + floatValue134.w);
    float quotientValue139 = (floatValue138 / floatValue137);
    float floatValue140 = (quotientValue139 + floatValue134.z);
    float floatValue141 = abs(floatValue140);
    float floatValue142 = (floatValue141 + asfloat(asuint(_ColorLutHueSaturationContrast).x));
    uint2 wordValue143 = uint2(0x00000000u, 0x00000000u);
    // _EF_LutCurve4：显式LOD采样，不能改成依赖屏幕导数的隐式LOD。
    float4 _sample0 = _EF_LutCurve4.SampleLevel(sampler_EFLut_linear_clamp,
                                                float2(floatValue142, asfloat(wordValue143.x)), asfloat(0x00000000u));
    float sampledValue144 = _sample0.x;
    // _EF_LutCurve5：显式LOD采样，不能改成依赖屏幕导数的隐式LOD。
    float4 _sample1 = _EF_LutCurve5.SampleLevel(sampler_EFLut_linear_clamp,
                                                float2(floatValue141, asfloat(wordValue143.y)), asfloat(0x00000000u));
    float sampledValue145 = _sample1.x;
    float2 floatValue146 = saturate(float2(sampledValue144, sampledValue145));
    float floatValue147 = (floatValue146.y + floatValue146.y);
    float floatValue148 = (floatValue142 + floatValue146.x);
    float3 floatValue149 = (float3(floatValue148, floatValue148, floatValue148) +
                            float3(asfloat(0xbf000000u), asfloat(0x3f000000u), asfloat(0xbfc00000u)));
    uint comparisonMask150 = (asfloat(0x3f800000u) < floatValue149.x ? 0xffffffffu : 0u);
    uint wordValue151 = (comparisonMask150 != 0u ? asuint(floatValue149.z) : asuint(floatValue149.x));
    uint comparisonMask152 = (floatValue149.x < asfloat(0x00000000u) ? 0xffffffffu : 0u);
    uint wordValue153 = (comparisonMask152 != 0u ? asuint(floatValue149.y) : wordValue151);
    float3 floatValue154 = (float3(asfloat(wordValue153), asfloat(wordValue153), asfloat(wordValue153)) +
                            float3(asfloat(0x3f800000u), asfloat(0x3f2aaaabu), asfloat(0x3eaaaaabu)));
    float3 floatValue155 = frac(float3(floatValue154.x, floatValue154.y, floatValue154.z));
    float3 floatValue156 = mad(float3(floatValue155.x, floatValue155.y, floatValue155.z),
                               float3(asfloat(0x40c00000u), asfloat(0x40c00000u), asfloat(0x40c00000u)),
                               float3(asfloat(0xc0400000u), asfloat(0xc0400000u), asfloat(0xc0400000u)));
    float3 floatValue157 = saturate((float3(abs(floatValue156.x), abs(floatValue156.y), abs(floatValue156.z)) +
                                     float3(asfloat(0xbf800000u), asfloat(0xbf800000u), asfloat(0xbf800000u))));
    float3 floatValue158 = (float3(floatValue157.x, floatValue157.y, floatValue157.z) +
                            float3(asfloat(0xbf800000u), asfloat(0xbf800000u), asfloat(0xbf800000u)));
    float floatValue159 = (floatValue134.x + asfloat(0x38d1b717u));
    float quotientValue160 = (floatValue136 / floatValue159);
    float3 floatValue161 = mad(float3(quotientValue160, quotientValue160, quotientValue160),
                               float3(floatValue158.x, floatValue158.y, floatValue158.z),
                               float3(asfloat(0x3f800000u), asfloat(0x3f800000u), asfloat(0x3f800000u)));
    float3 floatValue162 = (float3(floatValue134.x, floatValue134.x, floatValue134.x) *
                            float3(floatValue161.x, floatValue161.y, floatValue161.z));
    float dotProduct163 = dot(float3(floatValue162.x, floatValue162.y, floatValue162.z),
                              float3(asfloat(0x3e8b6199u), asfloat(0x3f2c90a3u), asfloat(0x3d5be985u)));
    float3 floatValue164 = mad(float3(floatValue161.x, floatValue161.y, floatValue161.z),
                               float3(floatValue134.x, floatValue134.x, floatValue134.x),
                               float3((-dotProduct163), (-dotProduct163), (-dotProduct163)));
    uint2 wordValue165 = uint2(0x00000000u, 0x00000000u);
    // _EF_LutCurve6：显式LOD采样，不能改成依赖屏幕导数的隐式LOD。
    float4 _sample2 = _EF_LutCurve6.SampleLevel(
        sampler_EFLut_linear_clamp, float2(quotientValue160, asfloat(wordValue165.x)), asfloat(0x00000000u));
    float sampledValue166 = _sample2.x;
    // _EF_LutCurve7：显式LOD采样，不能改成依赖屏幕导数的隐式LOD。
    float4 _sample3 = _EF_LutCurve7.SampleLevel(sampler_EFLut_linear_clamp,
                                                float2(dotProduct131, asfloat(wordValue165.y)), asfloat(0x00000000u));
    float sampledValue167 = _sample3.x;
    float2 floatValue168 = saturate(float2(sampledValue166, sampledValue167));
    float dotProduct169 = dot(float2(floatValue168.x, floatValue168.x), float2(floatValue147, floatValue147));
    float floatValue170 = (dotProduct169 * floatValue168.y);
    float dotProduct171 =
        dot(float2(asfloat(asuint(_ColorLutHueSaturationContrast).y), asfloat(asuint(_ColorLutHueSaturationContrast).y)), float2(floatValue170, floatValue170));
    float3 floatValue172 = mad(float3(dotProduct171, dotProduct171, dotProduct171),
                               float3(floatValue164.x, floatValue164.y, floatValue164.z),
                               float3(dotProduct163, dotProduct163, dotProduct163));
    float floatValue173 = max(floatValue172.y, floatValue172.x);
    float floatValue174 = max(floatValue172.z, floatValue173);
    float floatValue175 = (floatValue174 + asfloat(0x3f800000u));
    float quotientValue176 = (asfloat(0x3f800000u) / floatValue175);
    float3 floatValue177 = mad(float3(floatValue172.x, floatValue172.y, floatValue172.z),
                               float3(quotientValue176, quotientValue176, quotientValue176),
                               float3(asfloat(0x3b800000u), asfloat(0x3b800000u), asfloat(0x3b800000u)));
    uint wordValue178 = 0x00000000u;
    // _EF_LutCurve0：显式LOD采样，不能改成依赖屏幕导数的隐式LOD。
    float4 _sample4 = _EF_LutCurve0.SampleLevel(sampler_EFLut_linear_clamp,
                                                float2(floatValue177.x, asfloat(wordValue178)), asfloat(0x00000000u));
    float sampledValue179 = _sample4.x;
    float floatValue180 = saturate(sampledValue179);
    float4 _sample5 = _EF_LutCurve0.SampleLevel(sampler_EFLut_linear_clamp,
                                                float2(floatValue177.y, asfloat(wordValue178)), asfloat(0x00000000u));
    float sampledValue181 = _sample5.x;
    float4 _sample6 = _EF_LutCurve0.SampleLevel(sampler_EFLut_linear_clamp,
                                                float2(floatValue177.z, asfloat(wordValue178)), asfloat(0x00000000u));
    float sampledValue182 = _sample6.x;
    float2 floatValue183 = saturate(float2(sampledValue181, sampledValue182));
    float3 floatValue184 = (float3(floatValue180, floatValue183.x, floatValue183.y) +
                            float3(asfloat(0x3b800000u), asfloat(0x3b800000u), asfloat(0x3b800000u)));
    uint wordValue185 = 0x00000000u;
    // _EF_LutCurve1：显式LOD采样，不能改成依赖屏幕导数的隐式LOD。
    float4 _sample7 = _EF_LutCurve1.SampleLevel(sampler_EFLut_linear_clamp,
                                                float2(floatValue184.x, asfloat(wordValue185)), asfloat(0x00000000u));
    float sampledValue186 = _sample7.x;
    float floatValue187 = saturate(sampledValue186);
    // _EF_LutCurve2：显式LOD采样，不能改成依赖屏幕导数的隐式LOD。
    float4 _sample8 = _EF_LutCurve2.SampleLevel(sampler_EFLut_linear_clamp,
                                                float2(floatValue184.y, asfloat(wordValue185)), asfloat(0x00000000u));
    float sampledValue188 = _sample8.x;
    // _EF_LutCurve3：显式LOD采样，不能改成依赖屏幕导数的隐式LOD。
    float4 _sample9 = _EF_LutCurve3.SampleLevel(sampler_EFLut_linear_clamp,
                                                float2(floatValue184.z, asfloat(wordValue185)), asfloat(0x00000000u));
    float sampledValue189 = _sample9.x;
    float2 floatValue190 = saturate(float2(sampledValue188, sampledValue189));
    float floatValue191 = max(floatValue190.x, floatValue187);
    float floatValue192 = max(floatValue190.y, floatValue191);
    float floatValue193 = ((-floatValue192) + asfloat(0x3f800000u));
    float quotientValue194 = (asfloat(0x3f800000u) / floatValue193);
    float3 floatValue195 = (float3(quotientValue194, quotientValue194, quotientValue194) *
                            float3(floatValue187, floatValue190.x, floatValue190.y));
    float3 floatValue196 = mad(float3(floatValue195.x, floatValue195.y, floatValue195.z),
                               float3(asfloat(0x403be829u), asfloat(0x403be829u), asfloat(0x403be829u)),
                               float3(asfloat(0x3f631a6du), asfloat(0x3f631a6du), asfloat(0x3f631a6du)));
    float3 floatValue197 = mad(float3(floatValue195.x, floatValue195.y, floatValue195.z),
                               float3(floatValue196.x, floatValue196.y, floatValue196.z),
                               float3(asfloat(0x3f4e9047u), asfloat(0x3f4e9047u), asfloat(0x3f4e9047u)));
    float3 quotientValue198 = (float3(asfloat(0x3f800000u), asfloat(0x3f800000u), asfloat(0x3f800000u)) /
                               float3(floatValue197.x, floatValue197.y, floatValue197.z));
    float3 floatValue199 = max(float3(quotientValue198.x, quotientValue198.y, quotientValue198.z),
                               float3(asfloat(0x38d1b717u), asfloat(0x38d1b717u), asfloat(0x38d1b717u)));
    float3 floatValue200 = mad(float3(floatValue195.x, floatValue195.y, floatValue195.z),
                               float3(asfloat(0x40323ed5u), asfloat(0x40323ed5u), asfloat(0x40323ed5u)),
                               float3(asfloat(0x3ddcb791u), asfloat(0x3ddcb791u), asfloat(0x3ddcb791u)));
    float3 floatValue201 = (float3(floatValue195.x, floatValue195.y, floatValue195.z) *
                            float3(floatValue200.x, floatValue200.y, floatValue200.z));
    float dotProduct202 = dot(float3(floatValue195.x, floatValue195.y, floatValue195.z),
                              float3(asfloat(0x3e8b6199u), asfloat(0x3f2c90a3u), asfloat(0x3d5be985u)));
    float floatValue203 = (dotProduct202 + asfloat(0xbf000000u));
    float floatValue204 = saturate((floatValue203 * asfloat(0x3f2aaaabu)));
    float3 floatValue205 = (float3(floatValue199.x, floatValue199.y, floatValue199.z) *
                            float3(floatValue201.x, floatValue201.y, floatValue201.z));
    float3 floatValue206 = min(float3(floatValue205.x, floatValue205.y, floatValue205.z),
                               float3(asfloat(0x3f800000u), asfloat(0x3f800000u), asfloat(0x3f800000u)));
    float dotProduct207 = dot(float3(floatValue206.x, floatValue206.y, floatValue206.z),
                              float3(asfloat(0x3e8b6199u), asfloat(0x3f2c90a3u), asfloat(0x3d5be985u)));
    float3 floatValue208 = (float3(floatValue206.x, floatValue206.y, floatValue206.z) +
                            float3((-dotProduct207), (-dotProduct207), (-dotProduct207)));
    float3 floatValue209 = mad(float3(floatValue208.x, floatValue208.y, floatValue208.z),
                               float3(asfloat(0x3f6e147bu), asfloat(0x3f6e147bu), asfloat(0x3f6e147bu)),
                               float3(dotProduct207, dotProduct207, dotProduct207));
    float dotProduct210 = dot(float3(asfloat(0x3fda3f21u), asfloat(0xbf1f2dadu), asfloat(0xbdaa8387u)),
                              float3(floatValue209.x, floatValue209.y, floatValue209.z));
    float dotProduct211 = dot(float3(asfloat(0xbe056221u), asfloat(0x3f9205d4u), asfloat(0xbc2cd251u)),
                              float3(floatValue209.x, floatValue209.y, floatValue209.z));
    float dotProduct212 = dot(float3(asfloat(0xbcc4a281u), asfloat(0xbe041064u), asfloat(0x3f939493u)),
                              float3(floatValue209.x, floatValue209.y, floatValue209.z));
    float floatValue213 = max(dotProduct211, dotProduct210);
    float floatValue214 = max(dotProduct212, floatValue213);
    float floatValue215 = max(floatValue214, asfloat(0x3727c5acu));
    float3 quotientValue216 = saturate(
        (float3(dotProduct210, dotProduct211, dotProduct212) / float3(floatValue215, floatValue215, floatValue215)));
    float3 floatValue217 = (float3((-dotProduct210), (-dotProduct211), (-dotProduct212)) +
                            float3(quotientValue216.x, quotientValue216.y, quotientValue216.z));
    o0.xyz = asuint(saturate(mad(float3(floatValue204, floatValue204, floatValue204),
                                 float3(floatValue217.x, floatValue217.y, floatValue217.z),
                                 float3(dotProduct210, dotProduct211, dotProduct212))));
    // mov o0.w, l(0x3f800000)
    o0.w = 0x3f800000u;
    // 输出边界只恢复源通道的浮点视图；位载体在这里按原SV_Target/SV_Depth接口写出。
    _output0 = asfloat(o0.xyzw);
    controlWords0.xyzw =
        uint4(asuint(floatValue204), asuint(floatValue217.x), asuint(floatValue217.y), asuint(floatValue217.z));
    controlWords1.xyzw =
        uint4(asuint(dotProduct210), asuint(dotProduct211), asuint(dotProduct212), asuint(floatValue158.z));
    controlWords2.xyzw =
        uint4(asuint(floatValue201.x), asuint(floatValue201.y), asuint(floatValue201.z), wordValue165.y);
    controlWords3.xyzw =
        uint4(asuint(floatValue162.x), asuint(floatValue162.y), asuint(floatValue162.z), wordValue143.y);
    controlWords4.xyz = uint3(wordBits82.x, wordBits82.y, wordBits82.z);
    controlWords5.xyz = uint3(asuint(floatValue84.x), asuint(floatValue84.y), asuint(floatValue84.z));
    return;
}


#endif
