// 运行只接收语义材质、Unity矩阵与实时纹理；uint载体保留源算式跨分支位值。
// 带时间UV的分层表面的实际计算体；输入由Bindings和Geometry适配，输出保持源片元通道布局。
// uint载体保留寄存器位与掩码；asfloat/asuint不是数值转换，跨分支活跃分量不能提前覆盖。

// Character fragment graph: LayeredTimeUvSurface.
// Inputs: original interpolants and adapter-declared CB/resource slots.
// Intermediate float values are numeric; Words/masks retain raw 32-bit payloads.
// controlWords/controlValues carry live lanes across the original branch/loop edges.
// Samples, discard and output stores remain at their original control-flow positions.
void EFParticleEvaluateSoftLayer(float4 _input0 : SV_Position0, float4 _input1 : TEXCOORD0,
                                             float4 _input2 : TEXCOORD1, float4 _input3 : TEXCOORD2,
                                             float3 _input4 : TEXCOORD3, float3 _input5 : TEXCOORD4,
                                             nointerpolation uint _input6 : TEXCOORD5, out float4 _output0 : SV_Target0,
                                             out float4 _output1 : SV_Target1

)
{
    // Mutable state only carries values across original control-flow edges.
    uint4 controlWords0 = 0u;
    uint4 controlWords1 = 0u;
    uint4 controlWords2 = 0u;
    uint4 controlWords3 = 0u;
    uint4 v0 = 0u;
    uint4 v1 = 0u;
    uint4 v2 = 0u;
    uint4 v3 = 0u;
    uint4 v4 = 0u;
    uint4 v5 = 0u;
    uint4 v6 = 0u;
    uint4 o0 = 0u;
    uint4 o1 = 0u;
    // 把插值输入写入原寄存器载体；浮点值按位装入uint，整数及正反面掩码保留原类型。
    v0.xyzw = asuint(_input0);
    v1.xyzw = asuint(_input1);
    v2.xyzw = asuint(_input2);
    v3.xyzw = asuint(_input3);
    v4.xyz = asuint(_input4);
    v5.xyz = asuint(_input5);
    v6.x = _input6;
    uint2 wordValue0 = (uint2)(float2(asfloat(v0.x), asfloat(v0.y)));
    float2 floatValue1 = (float2)(uint2(wordValue0.x, wordValue0.y));
    float2 floatValue2 = (float2(floatValue1.x, floatValue1.y) * float2(asfloat(asuint(float4(_ScreenParams.xy,rcp(_ScreenParams.xy))).z), asfloat(asuint(float4(_ScreenParams.xy,rcp(_ScreenParams.xy))).w)));
    float2 floatValue3 = mad(float2(floatValue2.x, floatValue2.y), float2(asfloat(0x40000000u), asfloat(0x40000000u)),
                             float2(asfloat(0xbf800000u), asfloat(0xbf800000u)));
    float4 floatValue4 = (float4((-floatValue3.y), (-floatValue3.y), (-floatValue3.y), (-floatValue3.y)) *
                          float4(asfloat(EFParticleInverseViewColumn(1).x), asfloat(EFParticleInverseViewColumn(1).y), asfloat(EFParticleInverseViewColumn(1).z), asfloat(EFParticleInverseViewColumn(1).w)));
    float4 floatValue5 = mad(float4(asfloat(EFParticleInverseViewColumn(0).x), asfloat(EFParticleInverseViewColumn(0).y), asfloat(EFParticleInverseViewColumn(0).z), asfloat(EFParticleInverseViewColumn(0).w)),
                             float4(floatValue3.x, floatValue3.x, floatValue3.x, floatValue3.x),
                             float4(floatValue4.x, floatValue4.y, floatValue4.z, floatValue4.w));
    float2 floatValue6 = (float2(asfloat(v0.x), asfloat(v0.y)) * float2(asfloat(asuint(float4(_ScreenParams.xy,rcp(_ScreenParams.xy))).z), asfloat(asuint(float4(_ScreenParams.xy,rcp(_ScreenParams.xy))).w)));
    // 阶段：当前opaque深度，计算软交界。
    // _CameraDepthTexture：显式LOD采样，不能改成依赖屏幕导数的隐式LOD。
    float4 _sample0 = _CameraDepthTexture.SampleLevel(sampler_ParticlePointClamp, float2(floatValue6.x, floatValue6.y),
                                         asfloat(0x00000000u));
    float sampledValue7 = _sample0.x;
    float2 floatValue8 = mad(float2(floatValue6.x, floatValue6.y), float2(asfloat(0x40000000u), asfloat(0x40000000u)),
                             float2(asfloat(0xbf800000u), asfloat(0xbf800000u)));
    float4 floatValue9 = mad(float4(asfloat(EFParticleInverseViewColumn(2).x), asfloat(EFParticleInverseViewColumn(2).y), asfloat(EFParticleInverseViewColumn(2).z), asfloat(EFParticleInverseViewColumn(2).w)),
                             float4(sampledValue7, sampledValue7, sampledValue7, sampledValue7),
                             float4(floatValue5.x, floatValue5.y, floatValue5.z, floatValue5.w));
    float4 floatValue10 = (float4(floatValue9.x, floatValue9.y, floatValue9.z, floatValue9.w) +
                           float4(asfloat(EFParticleInverseViewColumn(3).x), asfloat(EFParticleInverseViewColumn(3).y), asfloat(EFParticleInverseViewColumn(3).z), asfloat(EFParticleInverseViewColumn(3).w)));
    float3 quotientValue11 = (float3(floatValue10.x, floatValue10.y, floatValue10.z) /
                              float3(floatValue10.w, floatValue10.w, floatValue10.w));
    float floatValue12 = (quotientValue11.y * asfloat(EFParticleViewColumn(1).z));
    float floatValue13 = mad(asfloat(EFParticleViewColumn(0).z), quotientValue11.x, floatValue12);
    float floatValue14 = mad(asfloat(EFParticleViewColumn(2).z), quotientValue11.z, floatValue13);
    float4 floatValue15 = (float4((-floatValue8.y), (-floatValue8.y), (-floatValue8.y), (-floatValue8.y)) *
                           float4(asfloat(EFParticleInverseViewColumn(1).x), asfloat(EFParticleInverseViewColumn(1).y), asfloat(EFParticleInverseViewColumn(1).z), asfloat(EFParticleInverseViewColumn(1).w)));
    float4 floatValue16 = mad(float4(asfloat(EFParticleInverseViewColumn(0).x), asfloat(EFParticleInverseViewColumn(0).y), asfloat(EFParticleInverseViewColumn(0).z), asfloat(EFParticleInverseViewColumn(0).w)),
                              float4(floatValue8.x, floatValue8.x, floatValue8.x, floatValue8.x),
                              float4(floatValue15.x, floatValue15.y, floatValue15.z, floatValue15.w));
    float4 floatValue17 = mad(float4(asfloat(EFParticleInverseViewColumn(2).x), asfloat(EFParticleInverseViewColumn(2).y), asfloat(EFParticleInverseViewColumn(2).z), asfloat(EFParticleInverseViewColumn(2).w)),
                              float4(asfloat(v0.z), asfloat(v0.z), asfloat(v0.z), asfloat(v0.z)),
                              float4(floatValue16.x, floatValue16.y, floatValue16.z, floatValue16.w));
    float4 floatValue18 = (float4(floatValue17.x, floatValue17.y, floatValue17.z, floatValue17.w) +
                           float4(asfloat(EFParticleInverseViewColumn(3).x), asfloat(EFParticleInverseViewColumn(3).y), asfloat(EFParticleInverseViewColumn(3).z), asfloat(EFParticleInverseViewColumn(3).w)));
    float3 quotientValue19 = (float3(floatValue18.x, floatValue18.y, floatValue18.z) /
                              float3(floatValue18.w, floatValue18.w, floatValue18.w));
    float floatValue20 = (quotientValue19.y * asfloat(EFParticleViewColumn(1).z));
    float floatValue21 = mad(asfloat(EFParticleViewColumn(0).z), quotientValue19.x, floatValue20);
    float floatValue22 = mad(asfloat(EFParticleViewColumn(2).z), quotientValue19.z, floatValue21);
    float2 floatValue23 = (float2(floatValue14, floatValue22) + float2(asfloat(EFParticleViewColumn(3).z), asfloat(EFParticleViewColumn(3).z)));
    float floatValue24 = ((-abs(floatValue23.y)) + abs(floatValue23.x));
    float2 floatValue25 =
        (float2(abs(floatValue23.y), abs(floatValue23.y)) + float2((-_ParticleNoiseResponse.y), (-_ParticleNoiseResponse.w)));
    float floatValue26 = (floatValue24 + _ParticleNoiseSampling.y);
    float quotientValue27 = saturate((floatValue26 / _ParticleNoiseSampling.x));
    float floatValue28 = (asfloat(v1.z) + _ParticleMaskResponse.y);
    float floatValue29 = mad(floatValue28, asfloat(0x400147aeu), asfloat(0xbc23d700u));
    float floatValue30 = (_ParticleMaskSampling.w * _ParticleMaskResponse.w);
    float floatValue31 = mad((-_ParticleMaskSampling.w), _ParticleMaskResponse.w, asfloat(0x3f800000u));
    float2 floatValue32 =
        (float2(asfloat(0x3f800000u), asfloat(0x3f800000u)) + float2((-_ParticleMaskUvControls.w), (-_ParticleMaskUvControls.z)));
    float floatValue33 = mad(floatValue32.y, floatValue30, floatValue31);
    float floatValue34 = mad(floatValue33, floatValue29, asfloat(0xbf800000u));
    float floatValue35 = saturate(((-floatValue34) * _ParticleMaskResponse.x));
    float floatValue36 = (floatValue34 + _ParticleMaskResponse.z);
    float floatValue37 = saturate((floatValue36 * _ParticleMaskResponse.x));
    uint wordValue38 = 0x3f800000u;
    float floatValue39 = trunc(_ParticlePrimarySampling.z);
    float floatValue40 = (floatValue39 + asfloat(asuint(float4(_ParticleMipBias,0,0,0)).x));
    // 阶段：主颜色层与UV采样。
    // _ParticleBaseMap：带原mip偏置采样，偏置与当前UV计算属于同一输入路径。
    float4 _sample1 =
        _ParticleBaseMap.SampleBias(sampler_ParticleLinearClamp, float2(asfloat(v1.x), asfloat(v1.y)), floatValue40);
    float4 sampledValue41 = _sample1.xyzw;
    uint wordValue42 = asuint(sampledValue41.x);
    float4 floatValue43 =
        (float4(asfloat(wordValue38), asfloat(wordValue38), asfloat(wordValue38), asfloat(wordValue42)) +
         float4((-sampledValue41.x), (-sampledValue41.y), (-sampledValue41.z), (-sampledValue41.w)));
    float4 floatValue44 = mad(float4(_ParticlePrimarySampling.y, _ParticlePrimarySampling.y, _ParticlePrimarySampling.y, _ParticlePrimarySampling.y),
                              float4(floatValue43.x, floatValue43.y, floatValue43.z, floatValue43.w),
                              float4(sampledValue41.x, sampledValue41.y, sampledValue41.z, sampledValue41.w));
    uint comparisonMask45 = (asfloat(0x00000000u) != _ParticleColorStreamControls.y ? 0xffffffffu : 0u);
    uint4 wordValue46 =
        uint4((comparisonMask45 != 0u ? 0x3f800000u : v3.x), (comparisonMask45 != 0u ? 0x3f800000u : v3.y),
              (comparisonMask45 != 0u ? 0x3f800000u : v3.z), (comparisonMask45 != 0u ? 0x3f800000u : v3.w));
    float4 floatValue47 =
        (float4(asfloat(wordValue46.x), asfloat(wordValue46.y), asfloat(wordValue46.z), asfloat(wordValue46.w)) *
         float4(_ParticlePrimaryTint.x, _ParticlePrimaryTint.y, _ParticlePrimaryTint.z, _ParticlePrimaryTint.w));
    float4 floatValue48 = (float4(floatValue47.x, floatValue47.y, floatValue47.z, floatValue47.w) *
                           float4(_ParticleColorStreamControls.z, _ParticleColorStreamControls.z, _ParticleColorStreamControls.z, _ParticleColorStreamControls.w));
    float4 floatValue49 = (float4(floatValue44.x, floatValue44.y, floatValue44.z, floatValue44.w) *
                           float4(floatValue48.x, floatValue48.y, floatValue48.z, floatValue48.w));
    float4 floatValue50 = (float4(floatValue32.x, floatValue32.x, floatValue32.x, floatValue32.x) *
                           float4(floatValue49.x, floatValue49.y, floatValue49.z, floatValue49.w));
    float floatValue51 = (floatValue35 * floatValue50.w);
    uint comparisonMask52 = (asfloat(0x00000000u) != _ParticleMaskTint.y ? 0xffffffffu : 0u);
    uint wordValue53 = (comparisonMask52 != 0u ? asuint(floatValue51) : asuint(floatValue50.w));
    float floatValue54 = (quotientValue27 * asfloat(wordValue53));
    float floatValue55 = ((-_ParticleNoiseResponse.y) + _ParticleNoiseResponse.z);
    float quotientValue56 = saturate((floatValue25.x / floatValue55));
    float floatValue57 = ((-_ParticleNoiseResponse.w) + _ParticleCoverageControl.x);
    float quotientValue58 = saturate((floatValue25.y / floatValue57));
    float floatValue59 = (quotientValue58 * quotientValue56);
    uint comparisonMask60 = (asfloat(0x00000000u) != _ParticleNoiseResponse.x ? 0xffffffffu : 0u);
    uint wordValue61 = (comparisonMask60 != 0u ? asuint(floatValue59) : 0x3f800000u);
    float floatValue62 = saturate((asfloat(wordValue61) * floatValue54));
    uint wordBits63 = (v6.x << (0x00000004u & 31u));
    float floatValue64 = (asfloat(0x3f800000u) + (-_ParticleInstanceCoverage.y));
    float floatValue65 = (floatValue64 * floatValue62);
    float dotProduct66 = dot(float2(asfloat(v0.x), asfloat(v0.y)), float2(asfloat(0x3d897143u), asfloat(0x3bbf4590u)));
    float floatValue67 = frac(dotProduct66);
    float floatValue68 = (floatValue67 * asfloat(0x4253ee82u));
    float floatValue69 = frac(floatValue68);
    uint comparisonMask70 = (_ParticleInstanceCoverage.x >= asfloat(0x00000000u) ? 0xffffffffu : 0u);
    uint wordValue71 = (comparisonMask70 != 0u ? asuint(floatValue69) : asuint((-floatValue69)));
    float floatValue72 = ((-asfloat(wordValue71)) + _ParticleInstanceCoverage.x);
    uint comparisonMask73 = (asfloat(0x00000000u) < floatValue72 ? 0xffffffffu : 0u);
    float2 floatValue74 =
        (float2(asfloat(0x3f800000u), asfloat(0x3f800000u)) + float2((-_ParticleBlendCoverage.x), (-_ParticleBlendCoverage.y)));
    uint wordValue75 = (comparisonMask73 != 0u ? 0x3f800000u : asuint(floatValue74.x));
    float floatValue76 = mad((-floatValue65), asfloat(wordValue75), asfloat(0x3f800000u));
    float floatValue77 = (asfloat(wordValue75) * floatValue65);
    float3 floatValue78 = (float3(floatValue37, floatValue37, floatValue37) *
                           float3(_ParticleSoftDepthControls.x, _ParticleSoftDepthControls.y, _ParticleSoftDepthControls.z));
    float3 floatValue79 = mad(float3(floatValue78.x, floatValue78.y, floatValue78.z),
                              float3(_ParticleColorStreamControls.z, _ParticleColorStreamControls.z, _ParticleColorStreamControls.z),
                              float3((-floatValue50.x), (-floatValue50.y), (-floatValue50.z)));
    float3 floatValue80 =
        mad(float3(floatValue37, floatValue37, floatValue37), float3(floatValue79.x, floatValue79.y, floatValue79.z),
            float3(floatValue50.x, floatValue50.y, floatValue50.z));
    uint3 wordValue81 = uint3((comparisonMask52 != 0u ? asuint(floatValue80.x) : asuint(floatValue50.x)),
                              (comparisonMask52 != 0u ? asuint(floatValue80.y) : asuint(floatValue50.y)),
                              (comparisonMask52 != 0u ? asuint(floatValue80.z) : asuint(floatValue50.z)));
    float3 floatValue82 = (float3(asfloat(wordValue81.x), asfloat(wordValue81.y), asfloat(wordValue81.z)) +
                           float3((-_ParticleHighlightResponse.y), (-_ParticleHighlightResponse.y), (-_ParticleHighlightResponse.y)));
    float3 floatValue83 = max(float3(floatValue82.x, floatValue82.y, floatValue82.z),
                              float3(asfloat(0x00000000u), asfloat(0x00000000u), asfloat(0x00000000u)));
    float3 floatValue84 = mad(float3(floatValue83.x, floatValue83.y, floatValue83.z),
                              float3(_ParticleHighlightResponse.z, _ParticleHighlightResponse.z, _ParticleHighlightResponse.z),
                              float3(asfloat(wordValue81.x), asfloat(wordValue81.y), asfloat(wordValue81.z)));
    float floatValue85 = (asfloat(0x3f800000u) + (-_ParticleExposureViewControls.x));
    float floatValue86 = mad(asfloat(asuint(float4(1,_EndfieldSceneExposure,_ScreenParams.x/_ScreenParams.y,0)).y), _ParticleExposureViewControls.x, floatValue85);
    float3 floatValue87 =
        (float3(floatValue86, floatValue86, floatValue86) * float3(floatValue84.x, floatValue84.y, floatValue84.z));
    float3 floatValue88 = max(float3(floatValue87.x, floatValue87.y, floatValue87.z),
                              float3(asfloat(0x00000000u), asfloat(0x00000000u), asfloat(0x00000000u)));
    float3 floatValue89 = min(float3(floatValue88.x, floatValue88.y, floatValue88.z),
                              float3(asfloat(0x447a0000u), asfloat(0x447a0000u), asfloat(0x447a0000u)));
    float3 floatValue90 =
        mad(float3(floatValue89.x, floatValue89.y, floatValue89.z), float3(floatValue77, floatValue77, floatValue77),
            float3(floatValue76, floatValue76, floatValue76));
    float3 floatValue91 =
        (float3(floatValue77, floatValue77, floatValue77) * float3(floatValue89.x, floatValue89.y, floatValue89.z));
    float dotProduct92 = dot(float3(floatValue89.x, floatValue89.y, floatValue89.z),
                             float3(asfloat(0x3e59c6edu), asfloat(0x3f371437u), asfloat(0x3d93d07du)));
    float floatValue93 = (floatValue77 * dotProduct92);
    uint comparisonMask94 = (asfloat(0x40000000u) == _ParticleBlendCoverage.y ? 0xffffffffu : 0u);
    uint3 wordValue95 = uint3((comparisonMask94 != 0u ? asuint(floatValue90.x) : asuint(floatValue91.x)),
                              (comparisonMask94 != 0u ? asuint(floatValue90.y) : asuint(floatValue91.y)),
                              (comparisonMask94 != 0u ? asuint(floatValue90.z) : asuint(floatValue91.z)));
    float dotProduct96 = dot(float3(asfloat(wordValue95.x), asfloat(wordValue95.y), asfloat(wordValue95.z)),
                             float3(asfloat(0x3e59c6edu), asfloat(0x3f371437u), asfloat(0x3d93d07du)));
    float3 floatValue97 = (float3(asfloat(wordValue95.x), asfloat(wordValue95.y), asfloat(wordValue95.z)) +
                           float3((-dotProduct96), (-dotProduct96), (-dotProduct96)));
    float3 floatValue98 =
        mad(float3(_ParticleOutputColorResponse.w, _ParticleOutputColorResponse.w, _ParticleOutputColorResponse.w),
            float3(floatValue97.x, floatValue97.y, floatValue97.z), float3(dotProduct96, dotProduct96, dotProduct96));
    float3 floatValue99 = (float3(floatValue98.x, floatValue98.y, floatValue98.z) *
                           float3(_ParticleOutputColorResponse.x, _ParticleOutputColorResponse.y, _ParticleOutputColorResponse.z));
    float floatValue100 = (asfloat(0x3f800000u) + (-_ParticleHighlightResponse.w));
    float3 floatValue101 = (float3(asfloat(wordValue95.x), asfloat(wordValue95.y), asfloat(wordValue95.z)) *
                            float3(floatValue100, floatValue100, floatValue100));
    o0.xyz = asuint(mad(float3(floatValue99.x, floatValue99.y, floatValue99.z),
                        float3(_ParticleHighlightResponse.w, _ParticleHighlightResponse.w, _ParticleHighlightResponse.w),
                        float3(floatValue101.x, floatValue101.y, floatValue101.z)));
    float floatValue102 = max(floatValue74.y, asfloat(0x00000000u));
    float floatValue103 = (floatValue74.y * floatValue77);
    o0.w = asuint((floatValue102 * floatValue77));
    float floatValue104 = max(floatValue103, floatValue93);
    float floatValue105 = saturate((floatValue104 * asfloat(0x41200000u)));
    uint comparisonMask106 = (asfloat(0x3f000000u) < floatValue105 ? 0xffffffffu : 0u);
    uint wordBits107 = (comparisonMask106 & 0x3f800000u);
    float floatValue108 = (_ParticleBlendCoverage.x * _ParticleBlendCoverage.z);
    o1.w = asuint((asfloat(wordBits107) * floatValue108));
    float floatValue109 = max(asfloat(v4.z), asfloat(0x322bcc77u));
    float2 quotientValue110 = (float2(asfloat(v4.x), asfloat(v4.y)) / float2(floatValue109, floatValue109));
    float floatValue111 = max(asfloat(v5.z), asfloat(0x322bcc77u));
    float2 quotientValue112 = (float2(asfloat(v5.x), asfloat(v5.y)) / float2(floatValue111, floatValue111));
    float2 floatValue113 =
        (float2((-quotientValue112.x), (-quotientValue112.y)) + float2(quotientValue110.x, quotientValue110.y));
    controlWords0.xyzw =
        uint4(asuint(floatValue113.x), asuint(floatValue113.y), asuint(quotientValue112.x), asuint(quotientValue112.y));
    controlWords1.xyzw =
        uint4(asuint(floatValue93), asuint(floatValue100), asuint(floatValue74.y), asuint(floatValue89.z));
    controlWords2.xyzw =
        uint4(asuint(floatValue99.x), asuint(floatValue99.y), asuint(floatValue99.z), asuint(floatValue50.w));
    controlWords3.xyzw =
        uint4(asuint(floatValue80.x), asuint(floatValue80.y), asuint(floatValue80.z), asuint(floatValue48.w));

    float floatValue115 = (-asfloat(controlWords0.y));
    uint2 comparisonMask116 = uint2((asfloat(0x00000000u) < asfloat(controlWords0.x) ? 0xffffffffu : 0u),
                                    (asfloat(0x00000000u) < floatValue115 ? 0xffffffffu : 0u));
    uint2 comparisonMask117 = uint2((asfloat(controlWords0.x) < asfloat(0x00000000u) ? 0xffffffffu : 0u),
                                    (floatValue115 < asfloat(0x00000000u) ? 0xffffffffu : 0u));
    float2 floatValue118 = (float2(asfloat(controlWords0.x), asfloat(controlWords0.y)) *
                            float2(asfloat(0x3f000000u), asfloat(0xbf000000u)));
    float2 squareRoot119 = sqrt(float2(abs(floatValue118.x), abs(floatValue118.y)));
    float2 squareRoot120 = sqrt(float2(squareRoot119.x, squareRoot119.y));
    uint2 wordValue121 = (int2((-asint(comparisonMask116.x)), (-asint(comparisonMask116.y))) +
                          uint2(comparisonMask117.x, comparisonMask117.y));
    float2 floatValue122 = (float2)(int2(asint(wordValue121.x), asint(wordValue121.y)));
    float2 floatValue123 = (float2(floatValue122.x, floatValue122.y) * float2(squareRoot120.x, squareRoot120.y));
    float2 floatValue124 =
        mad(float2(floatValue123.x, floatValue123.y), float2(asfloat(0x3f000000u), asfloat(0x3f000000u)),
            float2(asfloat(0x3f000000u), asfloat(0x3f000000u)));
    float floatValue125 = ((-_ParticleBlendCoverage.x) + _ParticleBlendCoverage.w);
    float floatValue126 = saturate((floatValue125 + asfloat(0x3f800000u)));
    uint comparisonMask127 = (asfloat(0x3f000000u) < floatValue126 ? 0xffffffffu : 0u);
    uint2 wordBits128 =
        (uint2(asuint(floatValue124.x), asuint(floatValue124.y)) & uint2(comparisonMask127, comparisonMask127));
    o1.xy = asuint(min(float2(asfloat(wordBits128.x), asfloat(wordBits128.y)),
                       float2(asfloat(0x3f800000u), asfloat(0x3f800000u))));
    // mov o1.z, l(0x3f800000)
    o1.z = 0x3f800000u;
    // 输出边界只恢复源通道的浮点视图；位载体在这里按原SV_Target/SV_Depth接口写出。
    _output0 = asfloat(o0.xyzw);
    _output1 = asfloat(o1.xyzw);
    controlWords0.xyzw = uint4(wordBits128.x, wordBits128.y, comparisonMask127, asuint(floatValue122.y));
    controlWords1.xy = uint2(comparisonMask116.x, comparisonMask116.y);
    return;
}
