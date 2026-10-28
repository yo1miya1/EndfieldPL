// 运行只接收语义材质、Unity矩阵与实时纹理；uint载体保留源算式跨分支位值。
// 带时间UV的分层表面的实际计算体；输入由Bindings和Geometry适配，输出保持源片元通道布局。
// uint载体保留寄存器位与掩码；asfloat/asuint不是数值转换，跨分支活跃分量不能提前覆盖。

// Character fragment graph: LayeredTimeUvSurface.
// Inputs: original interpolants and adapter-declared CB/resource slots.
// Intermediate float values are numeric; Words/masks retain raw 32-bit payloads.
// controlWords/controlValues carry live lanes across the original branch/loop edges.
// Samples, discard and output stores remain at their original control-flow positions.
void EFParticleEvaluateFourLayer(float4 _input0 : SV_Position0, float4 _input1 : TEXCOORD0,
                                             float4 _input2 : TEXCOORD1, float4 _input3 : TEXCOORD2,
                                             float4 _input4 : TEXCOORD3, float3 _input5 : TEXCOORD4,
                                             float3 _input6 : TEXCOORD5, nointerpolation uint _input7 : TEXCOORD6,
                                             out float4 _output0 : SV_Target0, out float4 _output1 : SV_Target1

)
{
    // Mutable state only carries values across original control-flow edges.
    uint4 controlWords0 = 0u;
    uint4 controlWords1 = 0u;
    uint4 controlWords2 = 0u;
    uint4 controlWords3 = 0u;
    uint4 controlWords4 = 0u;
    uint4 controlWords5 = 0u;
    uint4 controlWords6 = 0u;
    uint4 v0 = 0u;
    uint4 v1 = 0u;
    uint4 v2 = 0u;
    uint4 v3 = 0u;
    uint4 v4 = 0u;
    uint4 v5 = 0u;
    uint4 v6 = 0u;
    uint4 v7 = 0u;
    uint4 o0 = 0u;
    uint4 o1 = 0u;
    // 把插值输入写入原寄存器载体；浮点值按位装入uint，整数及正反面掩码保留原类型。
    v0.xyzw = asuint(_input0);
    v1.xyzw = asuint(_input1);
    v2.xyzw = asuint(_input2);
    v3.xyzw = asuint(_input3);
    v4.xyzw = asuint(_input4);
    v5.xyz = asuint(_input5);
    v6.xyz = asuint(_input6);
    v7.x = _input7;
    uint wordValue0 = 0x3f800000u;
    float floatValue1 = trunc(_ParticleMaskSampling.x);
    uint wordValue2 = 0x3f800000u;
    float floatValue3 = trunc(_ParticleNoiseSampling.x);
    float2 floatValue4 = (float2(floatValue1, floatValue3) + float2(asfloat(asuint(float4(_ParticleMipBias,0,0,0)).x), asfloat(asuint(float4(_ParticleMipBias,0,0,0)).x)));
    // 阶段：噪声层，驱动UV扭曲与覆盖率。
    // _ParticleNoiseMap：带原mip偏置采样，偏置与当前UV计算属于同一输入路径。
    float4 _sample0 =
        _ParticleNoiseMap.SampleBias(sampler_ParticleLinearRepeat, float2(asfloat(v2.x), asfloat(v2.y)), floatValue4.y);
    float4 sampledValue5 = _sample0.xyzw;
    uint wordValue6 = asuint(sampledValue5.x);
    float4 floatValue7 = (float4(asfloat(wordValue2), asfloat(wordValue2), asfloat(wordValue2), asfloat(wordValue6)) +
                          float4((-sampledValue5.x), (-sampledValue5.y), (-sampledValue5.z), (-sampledValue5.w)));
    float4 floatValue8 = mad(float4(_ParticleNoiseSampling.z, _ParticleNoiseSampling.z, _ParticleNoiseSampling.z, _ParticleNoiseSampling.z),
                             float4(floatValue7.x, floatValue7.y, floatValue7.z, floatValue7.w),
                             float4(sampledValue5.x, sampledValue5.y, sampledValue5.z, sampledValue5.w));
    float3 floatValue9 = (float3(asfloat(0x3f800000u), asfloat(0x3f800000u), asfloat(0x3f800000u)) +
                          float3((-_ParticleSoftIntersection.x), (-_ParticleSoftIntersection.z), (-_ParticleSoftIntersection.w)));
    float4 floatValue10 = mad(float4(floatValue8.x, floatValue8.y, floatValue8.w, floatValue8.x),
                              float4(_ParticleNoiseResponse.x, _ParticleNoiseResponse.x, _ParticleNoiseResponse.x, _ParticleNoiseResponse.y),
                              float4(floatValue9.x, floatValue9.x, floatValue9.x, floatValue9.y));
    float4 floatValue11 = mad(float4(floatValue8.x, floatValue8.y, floatValue8.z, floatValue8.w),
                              float4(_ParticleNoiseResponse.z, _ParticleNoiseResponse.z, _ParticleNoiseResponse.z, _ParticleNoiseResponse.z),
                              float4(floatValue9.z, floatValue9.z, floatValue9.z, floatValue9.z));
    float floatValue12 = (asfloat(0x3f800000u) + _ParticleSecondaryLayerInfluence.w);
    float floatValue13 = mad(floatValue10.x, floatValue12, (-_ParticleSecondaryLayerInfluence.w));
    float floatValue14 = (floatValue13 * floatValue10.z);
    float2 floatValue15 = mad(float2(floatValue14, floatValue10.y), float2(asfloat(0x40000000u), asfloat(0x40000000u)),
                              float2(asfloat(0xbf800000u), asfloat(0xbf800000u)));
    float4 floatValue16 = (float4(floatValue13, floatValue13, floatValue15.x, floatValue15.y) *
                           float4(_ParticleSecondaryDistortionMode.x, _ParticleSecondaryDistortionMode.y, _ParticleSecondaryDistortionMode.x, _ParticleSecondaryDistortionMode.x));
    uint2 comparisonMask17 = uint2((asfloat(0x00000000u) != _ParticleSecondaryLayerInfluence.z ? 0xffffffffu : 0u),
                                   (asfloat(0x00000000u) != _ParticleSecondaryLayerInfluence.y ? 0xffffffffu : 0u));
    uint wordValue18 = (comparisonMask17.x != 0u ? v1.w : 0x3f800000u);
    float4 floatValue19 =
        (float4(floatValue16.x, floatValue16.y, floatValue16.z, floatValue16.w) *
         float4(asfloat(wordValue18), asfloat(wordValue18), asfloat(wordValue18), asfloat(wordValue18)));
    uint2 comparisonMask20 = uint2((asfloat(0x00000000u) != _ParticleSecondaryDistortionScale.x ? 0xffffffffu : 0u),
                                   (asfloat(0x00000000u) != _ParticleSecondaryDistortionScale.y ? 0xffffffffu : 0u));
    uint2 wordValue21 = uint2((comparisonMask20.x != 0u ? asuint(floatValue19.z) : asuint(floatValue19.x)),
                              (comparisonMask20.x != 0u ? asuint(floatValue19.w) : asuint(floatValue19.y)));
    uint comparisonMask22 = (asfloat(0x00000000u) != _ParticleNoiseResponse.x ? 0xffffffffu : 0u);
    uint2 wordBits23 = (uint2(wordValue21.x, wordValue21.y) & uint2(comparisonMask22, comparisonMask22));
    float2 floatValue24 = mad(float2(asfloat(wordBits23.x), asfloat(wordBits23.y)),
                              float2(_ParticleMaskSampling.y, _ParticleMaskSampling.y), float2(asfloat(v2.z), asfloat(v2.w)));
    // 阶段：遮罩层，形成边缘与覆盖率。
    // _ParticleMaskMap：带原mip偏置采样，偏置与当前UV计算属于同一输入路径。
    float4 _sample1 =
        _ParticleMaskMap.SampleBias(sampler_ParticleLinearClamp, float2(floatValue24.x, floatValue24.y), floatValue4.x);
    float4 sampledValue25 = _sample1.xyzw;
    uint wordValue26 = asuint(sampledValue25.x);
    float4 floatValue27 = (float4(asfloat(wordValue0), asfloat(wordValue0), asfloat(wordValue0), asfloat(wordValue26)) +
                           float4((-sampledValue25.x), (-sampledValue25.y), (-sampledValue25.z), (-sampledValue25.w)));
    float4 floatValue28 = mad(float4(_ParticleMaskSampling.z, _ParticleMaskSampling.z, _ParticleMaskSampling.z, _ParticleMaskSampling.z),
                              float4(floatValue27.x, floatValue27.y, floatValue27.z, floatValue27.w),
                              float4(sampledValue25.x, sampledValue25.y, sampledValue25.z, sampledValue25.w));
    float floatValue29 = mad((-_ParticleSoftIntersection.x), _ParticleSoftIntersection.y, asfloat(0x3f800000u));
    float3 floatValue30 = mad(float3(floatValue28.x, floatValue28.y, floatValue28.w),
                              float3(_ParticleMaskResponse.x, _ParticleMaskResponse.x, _ParticleMaskResponse.x),
                              float3(floatValue29, floatValue29, floatValue29));
    float floatValue31 = mad(floatValue30.x, floatValue12, (-_ParticleSecondaryLayerInfluence.w));
    float floatValue32 = (floatValue31 * floatValue30.z);
    float2 floatValue33 = (float2(floatValue31, floatValue31) * float2(_ParticleSecondaryDistortionMode.z, _ParticleSecondaryDistortionMode.w));
    float2 floatValue34 =
        mad(float2(floatValue33.x, floatValue33.y), float2(asfloat(wordValue18), asfloat(wordValue18)),
            float2(asfloat(wordBits23.x), asfloat(wordBits23.y)));
    float2 floatValue35 = mad(float2(floatValue32, floatValue30.y), float2(asfloat(0x40000000u), asfloat(0x40000000u)),
                              float2(asfloat(0xbf800000u), asfloat(0xbf800000u)));
    float2 floatValue36 = (float2(floatValue35.x, floatValue35.y) * float2(_ParticleSecondaryDistortionMode.z, _ParticleSecondaryDistortionMode.z));
    float2 floatValue37 =
        mad(float2(floatValue36.x, floatValue36.y), float2(asfloat(wordValue18), asfloat(wordValue18)),
            float2(asfloat(wordBits23.x), asfloat(wordBits23.y)));
    uint2 wordValue38 = uint2((comparisonMask20.y != 0u ? asuint(floatValue37.x) : asuint(floatValue34.x)),
                              (comparisonMask20.y != 0u ? asuint(floatValue37.y) : asuint(floatValue34.y)));
    uint comparisonMask39 = (asfloat(0x00000000u) != _ParticleMaskResponse.x ? 0xffffffffu : 0u);
    uint2 wordValue40 = uint2((comparisonMask39 != 0u ? wordValue38.x : wordBits23.x),
                              (comparisonMask39 != 0u ? wordValue38.y : wordBits23.y));
    float floatValue41 = mad(floatValue28.x, _ParticleMaskResponse.y, floatValue10.w);
    float floatValue42 = (_ParticleMaskResponse.y * _ParticleSecondaryDistortionScale.w);
    float floatValue43 = (floatValue42 * _ParticleSecondaryDistortionScale.z);
    float floatValue44 = mad((-floatValue42), _ParticleSecondaryDistortionScale.z, asfloat(0x3f800000u));
    float floatValue45 = mad(floatValue41, floatValue43, floatValue44);
    float2 floatValue46 = (float2(floatValue45, floatValue45) * float2(asfloat(wordValue40.x), asfloat(wordValue40.y)));
    float2 floatValue47 = mad(float2(floatValue46.x, floatValue46.y), float2(_ParticleDepthFadeNear.y, _ParticleDepthFadeNear.y),
                              float2(asfloat(v3.x), asfloat(v3.y)));
    float floatValue48 = trunc(_ParticleDepthFadeNear.x);
    float floatValue49 = (floatValue48 + asfloat(asuint(float4(_ParticleMipBias,0,0,0)).x));
    // 阶段：叠加颜色层。
    // _ParticleOverlayMap：带原mip偏置采样，偏置与当前UV计算属于同一输入路径。
    float4 _sample2 =
        _ParticleOverlayMap.SampleBias(sampler_ParticleLinearClamp, float2(floatValue47.x, floatValue47.y), floatValue49);
    float4 sampledValue50 = _sample2.xyzw;
    uint wordValue51 = asuint(sampledValue50.x);
    uint wordValue52 = 0x3f800000u;
    float4 floatValue53 =
        (float4((-sampledValue50.x), (-sampledValue50.y), (-sampledValue50.z), (-sampledValue50.w)) +
         float4(asfloat(wordValue52), asfloat(wordValue52), asfloat(wordValue52), asfloat(wordValue51)));
    float4 floatValue54 = mad(float4(_ParticleDepthFadeNear.z, _ParticleDepthFadeNear.z, _ParticleDepthFadeNear.z, _ParticleDepthFadeNear.z),
                              float4(floatValue53.x, floatValue53.y, floatValue53.z, floatValue53.w),
                              float4(sampledValue50.x, sampledValue50.y, sampledValue50.z, sampledValue50.w));
    float floatValue55 = mad(floatValue54.x, _ParticleDepthFadeFar.x, floatValue41);
    float floatValue56 = (_ParticleDepthFadeFar.x * _ParticleSecondaryDistortionScale.w);
    float floatValue57 = (floatValue56 * _ParticleSecondaryDistortionScale.z);
    float floatValue58 = mad((-floatValue56), _ParticleSecondaryDistortionScale.z, asfloat(0x3f800000u));
    float floatValue59 = mad(floatValue55, floatValue57, floatValue58);
    float2 floatValue60 = (float2(floatValue59, floatValue59) * float2(floatValue46.x, floatValue46.y));
    float2 floatValue61 = mad(float2(floatValue60.x, floatValue60.y), float2(_ParticlePrimarySampling.x, _ParticlePrimarySampling.x),
                              float2(asfloat(v1.x), asfloat(v1.y)));
    float floatValue62 = trunc(_ParticlePrimarySampling.z);
    float floatValue63 = (floatValue62 + asfloat(asuint(float4(_ParticleMipBias,0,0,0)).x));
    // 阶段：主颜色层与UV采样。
    // _ParticleBaseMap：带原mip偏置采样，偏置与当前UV计算属于同一输入路径。
    float4 _sample3 =
        _ParticleBaseMap.SampleBias(sampler_ParticleLinearRepeat, float2(floatValue61.x, floatValue61.y), floatValue63);
    float4 sampledValue64 = _sample3.xyzw;
    uint wordValue65 = asuint(sampledValue64.x);
    uint wordValue66 = 0x3f800000u;
    float4 floatValue67 =
        (float4((-sampledValue64.x), (-sampledValue64.y), (-sampledValue64.z), (-sampledValue64.w)) +
         float4(asfloat(wordValue66), asfloat(wordValue66), asfloat(wordValue66), asfloat(wordValue65)));
    float4 floatValue68 = mad(float4(_ParticlePrimarySampling.y, _ParticlePrimarySampling.y, _ParticlePrimarySampling.y, _ParticlePrimarySampling.y),
                              float4(floatValue67.x, floatValue67.y, floatValue67.z, floatValue67.w),
                              float4(sampledValue64.x, sampledValue64.y, sampledValue64.z, sampledValue64.w));
    uint comparisonMask69 = (asfloat(0x00000000u) != _ParticleColorStreamControls.y ? 0xffffffffu : 0u);
    uint4 wordValue70 =
        uint4((comparisonMask69 != 0u ? 0x3f800000u : v4.x), (comparisonMask69 != 0u ? 0x3f800000u : v4.y),
              (comparisonMask69 != 0u ? 0x3f800000u : v4.z), (comparisonMask69 != 0u ? 0x3f800000u : v4.w));
    float4 floatValue71 =
        (float4(asfloat(wordValue70.x), asfloat(wordValue70.y), asfloat(wordValue70.z), asfloat(wordValue70.w)) *
         float4(_ParticlePrimaryTint.x, _ParticlePrimaryTint.y, _ParticlePrimaryTint.z, _ParticlePrimaryTint.w));
    float4 floatValue72 = (float4(floatValue71.x, floatValue71.y, floatValue71.z, floatValue71.w) *
                           float4(_ParticleColorStreamControls.z, _ParticleColorStreamControls.z, _ParticleColorStreamControls.z, _ParticleColorStreamControls.w));
    float4 floatValue73 = (float4(floatValue68.x, floatValue68.y, floatValue68.z, floatValue68.w) *
                           float4(floatValue72.x, floatValue72.y, floatValue72.z, floatValue72.w));
    float4 floatValue74 = mad(float4(floatValue28.x, floatValue28.y, floatValue28.z, floatValue28.w),
                              float4(_ParticleMaskResponse.z, _ParticleMaskResponse.z, _ParticleMaskResponse.z, _ParticleMaskResponse.z),
                              float4(floatValue11.x, floatValue11.y, floatValue11.z, floatValue11.w));
    float4 floatValue75 = mad(float4(floatValue54.x, floatValue54.y, floatValue54.z, floatValue54.w),
                              float4(_ParticleDepthFadeFar.y, _ParticleDepthFadeFar.y, _ParticleDepthFadeFar.y, _ParticleDepthFadeFar.y),
                              float4(floatValue74.x, floatValue74.y, floatValue74.z, floatValue74.w));
    float4 floatValue76 = (float4(floatValue54.x, floatValue54.y, floatValue54.z, floatValue54.w) *
                           float4(_ParticleDepthFadeFar.z, _ParticleDepthFadeFar.z, _ParticleDepthFadeFar.z, _ParticleDepthFadeFar.z));
    float4 floatValue77 = mad(float4(floatValue28.x, floatValue28.y, floatValue28.z, floatValue28.w),
                              float4(_ParticleMaskResponse.w, _ParticleMaskResponse.w, _ParticleMaskResponse.w, _ParticleMaskResponse.w),
                              float4(floatValue76.x, floatValue76.y, floatValue76.z, floatValue76.w));
    float floatValue78 = mad(floatValue73.w, floatValue75.w, floatValue77.w);
    float4 floatValue79 = (float4(floatValue75.x, floatValue75.y, floatValue75.z, floatValue75.w) *
                           float4(floatValue73.x, floatValue73.y, floatValue73.z, floatValue73.w));
    float floatValue80 = saturate((floatValue78 * _ParticleOverlayInfluence.w));
    float3 floatValue81 =
        (float3(floatValue80, floatValue80, floatValue80) * float3(floatValue77.x, floatValue77.y, floatValue77.z));
    float3 floatValue82 = mad(float3(floatValue81.x, floatValue81.y, floatValue81.z),
                              float3(_ParticleOverlayInfluence.x, _ParticleOverlayInfluence.y, _ParticleOverlayInfluence.z),
                              float3(floatValue79.x, floatValue79.y, floatValue79.z));
    float floatValue83 = (_ParticleSecondaryDistortionScale.w * _ParticleSecondaryDistortionFlags.w);
    float floatValue84 = mad((-_ParticleSecondaryDistortionScale.w), _ParticleSecondaryDistortionFlags.w, asfloat(0x3f800000u));
    float floatValue85 = mad(floatValue55, floatValue83, floatValue84);
    float floatValue86 = (asfloat(v1.z) + _ParticleSecondaryDistortionFlags.y);
    float floatValue87 = mad(floatValue86, asfloat(0x400147aeu), asfloat(0xbc23d700u));
    float floatValue88 = mad(floatValue85, floatValue87, asfloat(0xbf800000u));
    float floatValue89 = mad(floatValue54.x, _ParticleDepthFadeFar.w, (-floatValue88));
    float floatValue90 = ((-floatValue89) + _ParticleSecondaryDistortionFlags.z);
    float floatValue91 = saturate((floatValue89 * _ParticleSecondaryDistortionFlags.x));
    float floatValue92 = (floatValue91 * floatValue79.w);
    uint wordValue93 = (comparisonMask17.y != 0u ? asuint(floatValue92) : asuint(floatValue79.w));
    float floatValue94 = saturate((floatValue90 * _ParticleSecondaryDistortionFlags.x));
    float3 floatValue95 = (float3(floatValue94, floatValue94, floatValue94) *
                           float3(_ParticleOverlayResponse.x, _ParticleOverlayResponse.y, _ParticleOverlayResponse.z));
    float3 floatValue96 = mad(float3(floatValue95.x, floatValue95.y, floatValue95.z),
                              float3(_ParticleColorStreamControls.z, _ParticleColorStreamControls.z, _ParticleColorStreamControls.z),
                              float3((-floatValue82.x), (-floatValue82.y), (-floatValue82.z)));
    float3 floatValue97 =
        mad(float3(floatValue94, floatValue94, floatValue94), float3(floatValue96.x, floatValue96.y, floatValue96.z),
            float3(floatValue82.x, floatValue82.y, floatValue82.z));
    uint3 wordValue98 = uint3((comparisonMask17.y != 0u ? asuint(floatValue97.x) : asuint(floatValue82.x)),
                              (comparisonMask17.y != 0u ? asuint(floatValue97.y) : asuint(floatValue82.y)),
                              (comparisonMask17.y != 0u ? asuint(floatValue97.z) : asuint(floatValue82.z)));
    float3 floatValue99 = (float3(asfloat(wordValue98.x), asfloat(wordValue98.y), asfloat(wordValue98.z)) +
                           float3((-_ParticleHighlightResponse.y), (-_ParticleHighlightResponse.y), (-_ParticleHighlightResponse.y)));
    float3 floatValue100 = max(float3(floatValue99.x, floatValue99.y, floatValue99.z),
                               float3(asfloat(0x00000000u), asfloat(0x00000000u), asfloat(0x00000000u)));
    float3 floatValue101 = mad(float3(floatValue100.x, floatValue100.y, floatValue100.z),
                               float3(_ParticleHighlightResponse.z, _ParticleHighlightResponse.z, _ParticleHighlightResponse.z),
                               float3(asfloat(wordValue98.x), asfloat(wordValue98.y), asfloat(wordValue98.z)));
    float floatValue102 = (asfloat(0x3f800000u) + (-_ParticleExposureViewControls.x));
    float floatValue103 = mad(asfloat(asuint(float4(1,_EndfieldSceneExposure,_ScreenParams.x/_ScreenParams.y,0)).y), _ParticleExposureViewControls.x, floatValue102);
    float3 floatValue104 = (float3(floatValue101.x, floatValue101.y, floatValue101.z) *
                            float3(floatValue103, floatValue103, floatValue103));
    float3 floatValue105 = max(float3(floatValue104.x, floatValue104.y, floatValue104.z),
                               float3(asfloat(0x00000000u), asfloat(0x00000000u), asfloat(0x00000000u)));
    float3 floatValue106 = min(float3(floatValue105.x, floatValue105.y, floatValue105.z),
                               float3(asfloat(0x447a0000u), asfloat(0x447a0000u), asfloat(0x447a0000u)));
    float2 floatValue107 = (float2(asfloat(v0.x), asfloat(v0.y)) * float2(asfloat(asuint(float4(_ScreenParams.xy,rcp(_ScreenParams.xy))).z), asfloat(asuint(float4(_ScreenParams.xy,rcp(_ScreenParams.xy))).w)));
    float2 floatValue108 =
        mad(float2(floatValue107.x, floatValue107.y), float2(asfloat(0x40000000u), asfloat(0x40000000u)),
            float2(asfloat(0xbf800000u), asfloat(0xbf800000u)));
    float4 floatValue109 = (float4((-floatValue108.y), (-floatValue108.y), (-floatValue108.y), (-floatValue108.y)) *
                            float4(asfloat(EFParticleInverseViewColumn(1).x), asfloat(EFParticleInverseViewColumn(1).y), asfloat(EFParticleInverseViewColumn(1).z), asfloat(EFParticleInverseViewColumn(1).w)));
    float4 floatValue110 = mad(float4(asfloat(EFParticleInverseViewColumn(0).x), asfloat(EFParticleInverseViewColumn(0).y), asfloat(EFParticleInverseViewColumn(0).z), asfloat(EFParticleInverseViewColumn(0).w)),
                               float4(floatValue108.x, floatValue108.x, floatValue108.x, floatValue108.x),
                               float4(floatValue109.x, floatValue109.y, floatValue109.z, floatValue109.w));
    float4 floatValue111 = mad(float4(asfloat(EFParticleInverseViewColumn(2).x), asfloat(EFParticleInverseViewColumn(2).y), asfloat(EFParticleInverseViewColumn(2).z), asfloat(EFParticleInverseViewColumn(2).w)),
                               float4(asfloat(v0.z), asfloat(v0.z), asfloat(v0.z), asfloat(v0.z)),
                               float4(floatValue110.x, floatValue110.y, floatValue110.z, floatValue110.w));
    float4 floatValue112 = (float4(floatValue111.x, floatValue111.y, floatValue111.z, floatValue111.w) +
                            float4(asfloat(EFParticleInverseViewColumn(3).x), asfloat(EFParticleInverseViewColumn(3).y), asfloat(EFParticleInverseViewColumn(3).z), asfloat(EFParticleInverseViewColumn(3).w)));
    float3 quotientValue113 = (float3(floatValue112.x, floatValue112.y, floatValue112.z) /
                               float3(floatValue112.w, floatValue112.w, floatValue112.w));
    float floatValue114 = (quotientValue113.y * asfloat(EFParticleViewColumn(1).z));
    float floatValue115 = mad(asfloat(EFParticleViewColumn(0).z), quotientValue113.x, floatValue114);
    float floatValue116 = mad(asfloat(EFParticleViewColumn(2).z), quotientValue113.z, floatValue115);
    float floatValue117 = (floatValue116 + asfloat(EFParticleViewColumn(3).z));
    float2 floatValue118 =
        (float2(abs(floatValue117), abs(floatValue117)) + float2((-_ParticleDistortionScale.y), (-_ParticleDistortionScale.w)));
    float floatValue119 = ((-_ParticleDistortionScale.y) + _ParticleDistortionScale.z);
    float quotientValue120 = saturate((floatValue118.x / floatValue119));
    float floatValue121 = ((-_ParticleDistortionScale.w) + _ParticleDistortionFlags.x);
    float quotientValue122 = saturate((floatValue118.y / floatValue121));
    float floatValue123 = (quotientValue122 * quotientValue120);
    uint comparisonMask124 = (asfloat(0x00000000u) != _ParticleDistortionScale.x ? 0xffffffffu : 0u);
    uint wordValue125 = (comparisonMask124 != 0u ? asuint(floatValue123) : 0x3f800000u);
    float floatValue126 = saturate((asfloat(wordValue93) * asfloat(wordValue125)));
    uint wordBits127 = (v7.x << (0x00000004u & 31u));
    float floatValue128 = (asfloat(0x3f800000u) + (-_ParticleInstanceCoverage.y));
    float floatValue129 = (floatValue126 * floatValue128);
    float dotProduct130 = dot(float2(asfloat(v0.x), asfloat(v0.y)), float2(asfloat(0x3d897143u), asfloat(0x3bbf4590u)));
    float floatValue131 = frac(dotProduct130);
    float floatValue132 = (floatValue131 * asfloat(0x4253ee82u));
    float floatValue133 = frac(floatValue132);
    uint comparisonMask134 = (_ParticleInstanceCoverage.x >= asfloat(0x00000000u) ? 0xffffffffu : 0u);
    uint wordValue135 = (comparisonMask134 != 0u ? asuint(floatValue133) : asuint((-floatValue133)));
    float floatValue136 = ((-asfloat(wordValue135)) + _ParticleInstanceCoverage.x);
    uint comparisonMask137 = (asfloat(0x00000000u) < floatValue136 ? 0xffffffffu : 0u);
    float2 floatValue138 =
        (float2(asfloat(0x3f800000u), asfloat(0x3f800000u)) + float2((-_ParticleBlendCoverage.x), (-_ParticleBlendCoverage.y)));
    uint wordValue139 = (comparisonMask137 != 0u ? 0x3f800000u : asuint(floatValue138.x));
    float floatValue140 = mad((-floatValue129), asfloat(wordValue139), asfloat(0x3f800000u));
    float floatValue141 = (floatValue129 * asfloat(wordValue139));
    float3 floatValue142 =
        mad(float3(floatValue106.x, floatValue106.y, floatValue106.z),
            float3(floatValue141, floatValue141, floatValue141), float3(floatValue140, floatValue140, floatValue140));
    float3 floatValue143 = (float3(floatValue141, floatValue141, floatValue141) *
                            float3(floatValue106.x, floatValue106.y, floatValue106.z));
    float dotProduct144 = dot(float3(floatValue106.x, floatValue106.y, floatValue106.z),
                              float3(asfloat(0x3e59c6edu), asfloat(0x3f371437u), asfloat(0x3d93d07du)));
    float floatValue145 = (floatValue141 * dotProduct144);
    uint comparisonMask146 = (asfloat(0x40000000u) == _ParticleBlendCoverage.y ? 0xffffffffu : 0u);
    uint3 wordValue147 = uint3((comparisonMask146 != 0u ? asuint(floatValue142.x) : asuint(floatValue143.x)),
                               (comparisonMask146 != 0u ? asuint(floatValue142.y) : asuint(floatValue143.y)),
                               (comparisonMask146 != 0u ? asuint(floatValue142.z) : asuint(floatValue143.z)));
    float dotProduct148 = dot(float3(asfloat(wordValue147.x), asfloat(wordValue147.y), asfloat(wordValue147.z)),
                              float3(asfloat(0x3e59c6edu), asfloat(0x3f371437u), asfloat(0x3d93d07du)));
    float3 floatValue149 = (float3((-dotProduct148), (-dotProduct148), (-dotProduct148)) +
                            float3(asfloat(wordValue147.x), asfloat(wordValue147.y), asfloat(wordValue147.z)));
    float3 floatValue150 = mad(float3(_ParticleOutputColorResponse.w, _ParticleOutputColorResponse.w, _ParticleOutputColorResponse.w),
                               float3(floatValue149.x, floatValue149.y, floatValue149.z),
                               float3(dotProduct148, dotProduct148, dotProduct148));
    float3 floatValue151 = (float3(floatValue150.x, floatValue150.y, floatValue150.z) *
                            float3(_ParticleOutputColorResponse.x, _ParticleOutputColorResponse.y, _ParticleOutputColorResponse.z));
    float floatValue152 = (asfloat(0x3f800000u) + (-_ParticleHighlightResponse.w));
    float3 floatValue153 = (float3(floatValue152, floatValue152, floatValue152) *
                            float3(asfloat(wordValue147.x), asfloat(wordValue147.y), asfloat(wordValue147.z)));
    o0.xyz = asuint(mad(float3(floatValue151.x, floatValue151.y, floatValue151.z),
                        float3(_ParticleHighlightResponse.w, _ParticleHighlightResponse.w, _ParticleHighlightResponse.w),
                        float3(floatValue153.x, floatValue153.y, floatValue153.z)));
    float floatValue154 = max(floatValue138.y, asfloat(0x00000000u));
    float floatValue155 = (floatValue138.y * floatValue141);
    o0.w = asuint((floatValue154 * floatValue141));
    float floatValue156 = max(floatValue155, floatValue145);
    float floatValue157 = saturate((floatValue156 * asfloat(0x41200000u)));
    uint comparisonMask158 = (asfloat(0x3f000000u) < floatValue157 ? 0xffffffffu : 0u);
    uint wordBits159 = (comparisonMask158 & 0x3f800000u);
    float floatValue160 = (_ParticleBlendCoverage.x * _ParticleBlendCoverage.z);
    o1.w = asuint((asfloat(wordBits159) * floatValue160));
    float floatValue161 = max(asfloat(v5.z), asfloat(0x322bcc77u));
    float2 quotientValue162 = (float2(asfloat(v5.x), asfloat(v5.y)) / float2(floatValue161, floatValue161));
    float floatValue163 = max(asfloat(v6.z), asfloat(0x322bcc77u));
    float2 quotientValue164 = (float2(asfloat(v6.x), asfloat(v6.y)) / float2(floatValue163, floatValue163));
    float2 floatValue165 =
        (float2((-quotientValue164.x), (-quotientValue164.y)) + float2(quotientValue162.x, quotientValue162.y));
    controlWords0.xyzw =
        uint4(asuint(floatValue165.x), asuint(floatValue165.y), asuint(quotientValue164.x), asuint(quotientValue164.y));
    controlWords1.xyzw =
        uint4(asuint(floatValue153.x), asuint(floatValue153.y), asuint(floatValue138.y), asuint(floatValue153.z));
    controlWords2.xyzw =
        uint4(asuint(floatValue151.x), asuint(floatValue151.y), asuint(floatValue151.z), asuint(floatValue109.w));
    controlWords3.xyzw = uint4(asuint(floatValue57), comparisonMask17.y, asuint(floatValue10.z), wordValue51);
    controlWords4.xyzw =
        uint4(asuint(floatValue73.x), asuint(floatValue73.y), asuint(floatValue73.z), asuint(floatValue73.w));
    controlWords5.xyzw =
        uint4(asuint(floatValue77.x), asuint(floatValue77.y), asuint(floatValue77.z), asuint(floatValue77.w));
    controlWords6.xyzw =
        uint4(asuint(floatValue76.x), asuint(floatValue76.y), asuint(floatValue76.z), asuint(floatValue76.w));

    float floatValue167 = (-asfloat(controlWords0.y));
    uint2 comparisonMask168 = uint2((asfloat(0x00000000u) < asfloat(controlWords0.x) ? 0xffffffffu : 0u),
                                    (asfloat(0x00000000u) < floatValue167 ? 0xffffffffu : 0u));
    uint2 comparisonMask169 = uint2((asfloat(controlWords0.x) < asfloat(0x00000000u) ? 0xffffffffu : 0u),
                                    (floatValue167 < asfloat(0x00000000u) ? 0xffffffffu : 0u));
    float2 floatValue170 = (float2(asfloat(controlWords0.x), asfloat(controlWords0.y)) *
                            float2(asfloat(0x3f000000u), asfloat(0xbf000000u)));
    float2 squareRoot171 = sqrt(float2(abs(floatValue170.x), abs(floatValue170.y)));
    float2 squareRoot172 = sqrt(float2(squareRoot171.x, squareRoot171.y));
    uint2 wordValue173 = (int2((-asint(comparisonMask168.x)), (-asint(comparisonMask168.y))) +
                          uint2(comparisonMask169.x, comparisonMask169.y));
    float2 floatValue174 = (float2)(int2(asint(wordValue173.x), asint(wordValue173.y)));
    float2 floatValue175 = (float2(floatValue174.x, floatValue174.y) * float2(squareRoot172.x, squareRoot172.y));
    float2 floatValue176 =
        mad(float2(floatValue175.x, floatValue175.y), float2(asfloat(0x3f000000u), asfloat(0x3f000000u)),
            float2(asfloat(0x3f000000u), asfloat(0x3f000000u)));
    float floatValue177 = ((-_ParticleBlendCoverage.x) + _ParticleBlendCoverage.w);
    float floatValue178 = saturate((floatValue177 + asfloat(0x3f800000u)));
    uint comparisonMask179 = (asfloat(0x3f000000u) < floatValue178 ? 0xffffffffu : 0u);
    uint2 wordBits180 =
        (uint2(asuint(floatValue176.x), asuint(floatValue176.y)) & uint2(comparisonMask179, comparisonMask179));
    o1.xy = asuint(min(float2(asfloat(wordBits180.x), asfloat(wordBits180.y)),
                       float2(asfloat(0x3f800000u), asfloat(0x3f800000u))));
    // mov o1.z, l(0x3f800000)
    o1.z = 0x3f800000u;
    // 输出边界只恢复源通道的浮点视图；位载体在这里按原SV_Target/SV_Depth接口写出。
    _output0 = asfloat(o0.xyzw);
    _output1 = asfloat(o1.xyzw);
    controlWords0.xyzw = uint4(wordBits180.x, wordBits180.y, comparisonMask179, asuint(floatValue174.y));
    controlWords1.xy = uint2(comparisonMask168.x, comparisonMask168.y);
    return;
}
