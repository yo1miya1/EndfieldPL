// 运行只接收语义材质、Unity矩阵与实时纹理；uint载体保留源算式跨分支位值。
// 带时间UV的分层表面的实际计算体；输入由Bindings和Geometry适配，输出保持源片元通道布局。
// uint载体保留寄存器位与掩码；asfloat/asuint不是数值转换，跨分支活跃分量不能提前覆盖。

// Character fragment graph: LayeredTimeUvSurface.
// Inputs: original interpolants and adapter-declared CB/resource slots.
// Intermediate float values are numeric; Words/masks retain raw 32-bit payloads.
// controlWords/controlValues carry live lanes across the original branch/loop edges.
// Samples, discard and output stores remain at their original control-flow positions.
void EFParticleEvaluateFourLayerShift(float4 _input0 : SV_Position0, float4 _input1 : TEXCOORD0,
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
                          float3((-_ParticleSecondaryLayerInfluence.x), (-_ParticleSecondaryLayerInfluence.z), (-_ParticleSecondaryLayerInfluence.w)));
    float4 floatValue10 = mad(float4(floatValue8.x, floatValue8.y, floatValue8.w, floatValue8.x),
                              float4(_ParticleNoiseResponse.x, _ParticleNoiseResponse.x, _ParticleNoiseResponse.x, _ParticleNoiseResponse.y),
                              float4(floatValue9.x, floatValue9.x, floatValue9.x, floatValue9.y));
    float4 floatValue11 = mad(float4(floatValue8.x, floatValue8.y, floatValue8.z, floatValue8.w),
                              float4(_ParticleNoiseResponse.z, _ParticleNoiseResponse.z, _ParticleNoiseResponse.z, _ParticleNoiseResponse.z),
                              float4(floatValue9.z, floatValue9.z, floatValue9.z, floatValue9.z));
    float floatValue12 = (asfloat(0x3f800000u) + _ParticleSecondaryDistortionMode.w);
    float floatValue13 = mad(floatValue10.x, floatValue12, (-_ParticleSecondaryDistortionMode.w));
    float floatValue14 = (floatValue13 * floatValue10.z);
    float2 floatValue15 = mad(float2(floatValue14, floatValue10.y), float2(asfloat(0x40000000u), asfloat(0x40000000u)),
                              float2(asfloat(0xbf800000u), asfloat(0xbf800000u)));
    float4 floatValue16 = (float4(floatValue13, floatValue13, floatValue15.x, floatValue15.y) *
                           float4(_ParticleSecondaryDistortionScale.x, _ParticleSecondaryDistortionScale.y, _ParticleSecondaryDistortionScale.x, _ParticleSecondaryDistortionScale.x));
    uint2 comparisonMask17 = uint2((asfloat(0x00000000u) != _ParticleSecondaryDistortionMode.z ? 0xffffffffu : 0u),
                                   (asfloat(0x00000000u) != _ParticleSecondaryDistortionMode.y ? 0xffffffffu : 0u));
    uint wordValue18 = (comparisonMask17.x != 0u ? v1.w : 0x3f800000u);
    float4 floatValue19 =
        (float4(floatValue16.x, floatValue16.y, floatValue16.z, floatValue16.w) *
         float4(asfloat(wordValue18), asfloat(wordValue18), asfloat(wordValue18), asfloat(wordValue18)));
    uint2 comparisonMask20 = uint2((asfloat(0x00000000u) != _ParticleSecondaryDistortionFlags.x ? 0xffffffffu : 0u),
                                   (asfloat(0x00000000u) != _ParticleSecondaryDistortionFlags.y ? 0xffffffffu : 0u));
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
    float floatValue29 = mad((-_ParticleSecondaryLayerInfluence.x), _ParticleSecondaryLayerInfluence.y, asfloat(0x3f800000u));
    float3 floatValue30 = mad(float3(floatValue28.x, floatValue28.y, floatValue28.w),
                              float3(_ParticleMaskResponse.x, _ParticleMaskResponse.x, _ParticleMaskResponse.x),
                              float3(floatValue29, floatValue29, floatValue29));
    float floatValue31 = mad(floatValue30.x, floatValue12, (-_ParticleSecondaryDistortionMode.w));
    float floatValue32 = (floatValue31 * floatValue30.z);
    float2 floatValue33 = (float2(floatValue31, floatValue31) * float2(_ParticleSecondaryDistortionScale.z, _ParticleSecondaryDistortionScale.w));
    float2 floatValue34 =
        mad(float2(floatValue33.x, floatValue33.y), float2(asfloat(wordValue18), asfloat(wordValue18)),
            float2(asfloat(wordBits23.x), asfloat(wordBits23.y)));
    float2 floatValue35 = mad(float2(floatValue32, floatValue30.y), float2(asfloat(0x40000000u), asfloat(0x40000000u)),
                              float2(asfloat(0xbf800000u), asfloat(0xbf800000u)));
    float2 floatValue36 = (float2(floatValue35.x, floatValue35.y) * float2(_ParticleSecondaryDistortionScale.z, _ParticleSecondaryDistortionScale.z));
    float2 floatValue37 =
        mad(float2(floatValue36.x, floatValue36.y), float2(asfloat(wordValue18), asfloat(wordValue18)),
            float2(asfloat(wordBits23.x), asfloat(wordBits23.y)));
    uint2 wordValue38 = uint2((comparisonMask20.y != 0u ? asuint(floatValue37.x) : asuint(floatValue34.x)),
                              (comparisonMask20.y != 0u ? asuint(floatValue37.y) : asuint(floatValue34.y)));
    uint comparisonMask39 = (asfloat(0x00000000u) != _ParticleMaskResponse.x ? 0xffffffffu : 0u);
    uint2 wordValue40 = uint2((comparisonMask39 != 0u ? wordValue38.x : wordBits23.x),
                              (comparisonMask39 != 0u ? wordValue38.y : wordBits23.y));
    float floatValue41 = mad(floatValue28.x, _ParticleMaskResponse.y, floatValue10.w);
    float floatValue42 = (_ParticleMaskResponse.y * _ParticleSecondaryDistortionFlags.w);
    float floatValue43 = (floatValue42 * _ParticleSecondaryDistortionFlags.z);
    float floatValue44 = mad((-floatValue42), _ParticleSecondaryDistortionFlags.z, asfloat(0x3f800000u));
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
    float floatValue56 = (_ParticleDepthFadeFar.x * _ParticleSecondaryDistortionFlags.w);
    float floatValue57 = (floatValue56 * _ParticleSecondaryDistortionFlags.z);
    float floatValue58 = mad((-floatValue56), _ParticleSecondaryDistortionFlags.z, asfloat(0x3f800000u));
    float floatValue59 = mad(floatValue55, floatValue57, floatValue58);
    float2 floatValue60 = (float2(floatValue59, floatValue59) * float2(floatValue46.x, floatValue46.y));
    float2 floatValue61 = mad(float2(floatValue60.x, floatValue60.y), float2(_ParticlePrimarySampling.x, _ParticlePrimarySampling.x),
                              float2(asfloat(v1.x), asfloat(v1.y)));
    float floatValue62 = trunc(_ParticlePrimarySampling.z);
    float floatValue63 = (floatValue62 + asfloat(asuint(float4(_ParticleMipBias,0,0,0)).x));
    // 阶段：主颜色层与UV采样。
    // _ParticleBaseMap：带原mip偏置采样，偏置与当前UV计算属于同一输入路径。
    float4 _sample3 =
        _ParticleBaseMap.SampleBias(sampler_ParticleLinearClamp, float2(floatValue61.x, floatValue61.y), floatValue63);
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
    float floatValue80 = saturate((floatValue78 * _ParticleOverlayResponse.w));
    float3 floatValue81 =
        (float3(floatValue80, floatValue80, floatValue80) * float3(floatValue77.x, floatValue77.y, floatValue77.z));
    float3 floatValue82 = mad(float3(floatValue81.x, floatValue81.y, floatValue81.z),
                              float3(_ParticleOverlayResponse.x, _ParticleOverlayResponse.y, _ParticleOverlayResponse.z),
                              float3(floatValue79.x, floatValue79.y, floatValue79.z));
    float floatValue83 = (_ParticleSecondaryDistortionFlags.w * _ParticleSecondarySampling.w);
    float floatValue84 = mad((-_ParticleSecondaryDistortionFlags.w), _ParticleSecondarySampling.w, asfloat(0x3f800000u));
    float floatValue85 = mad(floatValue55, floatValue83, floatValue84);
    float floatValue86 = (asfloat(v1.z) + _ParticleSecondarySampling.y);
    float floatValue87 = mad(floatValue86, asfloat(0x400147aeu), asfloat(0xbc23d700u));
    float floatValue88 = mad(floatValue85, floatValue87, asfloat(0xbf800000u));
    float floatValue89 = mad(floatValue54.x, _ParticleDepthFadeFar.w, (-floatValue88));
    float floatValue90 = ((-floatValue89) + _ParticleSecondarySampling.z);
    float floatValue91 = saturate((floatValue89 * _ParticleSecondarySampling.x));
    float floatValue92 = (floatValue91 * floatValue79.w);
    uint wordValue93 = (comparisonMask17.y != 0u ? asuint(floatValue92) : asuint(floatValue79.w));
    float floatValue94 = saturate((floatValue90 * _ParticleSecondarySampling.x));
    float3 floatValue95 = (float3(floatValue94, floatValue94, floatValue94) *
                           float3(_ParticleOverlayTint.x, _ParticleOverlayTint.y, _ParticleOverlayTint.z));
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
    uint2 wordValue107 = (uint2)(float2(asfloat(v0.x), asfloat(v0.y)));
    float2 floatValue108 = (float2)(uint2(wordValue107.x, wordValue107.y));
    float2 floatValue109 = (float2(floatValue108.x, floatValue108.y) * float2(asfloat(asuint(float4(_ScreenParams.xy,rcp(_ScreenParams.xy))).z), asfloat(asuint(float4(_ScreenParams.xy,rcp(_ScreenParams.xy))).w)));
    float2 floatValue110 =
        mad(float2(floatValue109.x, floatValue109.y), float2(asfloat(0x40000000u), asfloat(0x40000000u)),
            float2(asfloat(0xbf800000u), asfloat(0xbf800000u)));
    float4 floatValue111 = (float4((-floatValue110.y), (-floatValue110.y), (-floatValue110.y), (-floatValue110.y)) *
                            float4(asfloat(EFParticleInverseViewColumn(1).x), asfloat(EFParticleInverseViewColumn(1).y), asfloat(EFParticleInverseViewColumn(1).z), asfloat(EFParticleInverseViewColumn(1).w)));
    float4 floatValue112 = mad(float4(asfloat(EFParticleInverseViewColumn(0).x), asfloat(EFParticleInverseViewColumn(0).y), asfloat(EFParticleInverseViewColumn(0).z), asfloat(EFParticleInverseViewColumn(0).w)),
                               float4(floatValue110.x, floatValue110.x, floatValue110.x, floatValue110.x),
                               float4(floatValue111.x, floatValue111.y, floatValue111.z, floatValue111.w));
    float2 floatValue113 = (float2(asfloat(v0.x), asfloat(v0.y)) * float2(asfloat(asuint(float4(_ScreenParams.xy,rcp(_ScreenParams.xy))).z), asfloat(asuint(float4(_ScreenParams.xy,rcp(_ScreenParams.xy))).w)));
    // 阶段：当前opaque深度，计算软交界。
    // _CameraDepthTexture：显式LOD采样，不能改成依赖屏幕导数的隐式LOD。
    float4 _sample4 = _CameraDepthTexture.SampleLevel(sampler_ParticlePointClamp, float2(floatValue113.x, floatValue113.y),
                                         asfloat(0x00000000u));
    float sampledValue114 = _sample4.x;
    float2 floatValue115 =
        mad(float2(floatValue113.x, floatValue113.y), float2(asfloat(0x40000000u), asfloat(0x40000000u)),
            float2(asfloat(0xbf800000u), asfloat(0xbf800000u)));
    float4 floatValue116 = mad(float4(asfloat(EFParticleInverseViewColumn(2).x), asfloat(EFParticleInverseViewColumn(2).y), asfloat(EFParticleInverseViewColumn(2).z), asfloat(EFParticleInverseViewColumn(2).w)),
                               float4(sampledValue114, sampledValue114, sampledValue114, sampledValue114),
                               float4(floatValue112.x, floatValue112.y, floatValue112.z, floatValue112.w));
    float4 floatValue117 = (float4(floatValue116.x, floatValue116.y, floatValue116.z, floatValue116.w) +
                            float4(asfloat(EFParticleInverseViewColumn(3).x), asfloat(EFParticleInverseViewColumn(3).y), asfloat(EFParticleInverseViewColumn(3).z), asfloat(EFParticleInverseViewColumn(3).w)));
    float3 quotientValue118 = (float3(floatValue117.x, floatValue117.y, floatValue117.z) /
                               float3(floatValue117.w, floatValue117.w, floatValue117.w));
    float floatValue119 = (quotientValue118.y * asfloat(EFParticleViewColumn(1).z));
    float floatValue120 = mad(asfloat(EFParticleViewColumn(0).z), quotientValue118.x, floatValue119);
    float floatValue121 = mad(asfloat(EFParticleViewColumn(2).z), quotientValue118.z, floatValue120);
    float4 floatValue122 = (float4((-floatValue115.y), (-floatValue115.y), (-floatValue115.y), (-floatValue115.y)) *
                            float4(asfloat(EFParticleInverseViewColumn(1).x), asfloat(EFParticleInverseViewColumn(1).y), asfloat(EFParticleInverseViewColumn(1).z), asfloat(EFParticleInverseViewColumn(1).w)));
    float4 floatValue123 = mad(float4(asfloat(EFParticleInverseViewColumn(0).x), asfloat(EFParticleInverseViewColumn(0).y), asfloat(EFParticleInverseViewColumn(0).z), asfloat(EFParticleInverseViewColumn(0).w)),
                               float4(floatValue115.x, floatValue115.x, floatValue115.x, floatValue115.x),
                               float4(floatValue122.x, floatValue122.y, floatValue122.z, floatValue122.w));
    float4 floatValue124 = mad(float4(asfloat(EFParticleInverseViewColumn(2).x), asfloat(EFParticleInverseViewColumn(2).y), asfloat(EFParticleInverseViewColumn(2).z), asfloat(EFParticleInverseViewColumn(2).w)),
                               float4(asfloat(v0.z), asfloat(v0.z), asfloat(v0.z), asfloat(v0.z)),
                               float4(floatValue123.x, floatValue123.y, floatValue123.z, floatValue123.w));
    float4 floatValue125 = (float4(floatValue124.x, floatValue124.y, floatValue124.z, floatValue124.w) +
                            float4(asfloat(EFParticleInverseViewColumn(3).x), asfloat(EFParticleInverseViewColumn(3).y), asfloat(EFParticleInverseViewColumn(3).z), asfloat(EFParticleInverseViewColumn(3).w)));
    float3 quotientValue126 = (float3(floatValue125.x, floatValue125.y, floatValue125.z) /
                               float3(floatValue125.w, floatValue125.w, floatValue125.w));
    float floatValue127 = (quotientValue126.y * asfloat(EFParticleViewColumn(1).z));
    float floatValue128 = mad(asfloat(EFParticleViewColumn(0).z), quotientValue126.x, floatValue127);
    float floatValue129 = mad(asfloat(EFParticleViewColumn(2).z), quotientValue126.z, floatValue128);
    float2 floatValue130 = (float2(floatValue121, floatValue129) + float2(asfloat(EFParticleViewColumn(3).z), asfloat(EFParticleViewColumn(3).z)));
    float floatValue131 = ((-abs(floatValue130.y)) + abs(floatValue130.x));
    float2 floatValue132 =
        (float2(abs(floatValue130.y), abs(floatValue130.y)) + float2((-_ParticleDistortionFlags.y), (-_ParticleDistortionFlags.w)));
    float floatValue133 = (floatValue131 + _ParticleDistortionScale.y);
    float quotientValue134 = saturate((floatValue133 / _ParticleDistortionScale.x));
    float floatValue135 = (asfloat(wordValue93) * quotientValue134);
    float floatValue136 = ((-_ParticleDistortionFlags.y) + _ParticleDistortionFlags.z);
    float quotientValue137 = saturate((floatValue132.x / floatValue136));
    float floatValue138 = ((-_ParticleDistortionFlags.w) + _ParticleSoftIntersection.x);
    float quotientValue139 = saturate((floatValue132.y / floatValue138));
    float floatValue140 = (quotientValue139 * quotientValue137);
    uint comparisonMask141 = (asfloat(0x00000000u) != _ParticleDistortionFlags.x ? 0xffffffffu : 0u);
    uint wordValue142 = (comparisonMask141 != 0u ? asuint(floatValue140) : 0x3f800000u);
    float floatValue143 = saturate((floatValue135 * asfloat(wordValue142)));
    uint wordBits144 = (v7.x << (0x00000004u & 31u));
    float floatValue145 = (asfloat(0x3f800000u) + (-_ParticleInstanceCoverage.y));
    float floatValue146 = (floatValue143 * floatValue145);
    float dotProduct147 = dot(float2(asfloat(v0.x), asfloat(v0.y)), float2(asfloat(0x3d897143u), asfloat(0x3bbf4590u)));
    float floatValue148 = frac(dotProduct147);
    float floatValue149 = (floatValue148 * asfloat(0x4253ee82u));
    float floatValue150 = frac(floatValue149);
    uint comparisonMask151 = (_ParticleInstanceCoverage.x >= asfloat(0x00000000u) ? 0xffffffffu : 0u);
    uint wordValue152 = (comparisonMask151 != 0u ? asuint(floatValue150) : asuint((-floatValue150)));
    float floatValue153 = ((-asfloat(wordValue152)) + _ParticleInstanceCoverage.x);
    uint comparisonMask154 = (asfloat(0x00000000u) < floatValue153 ? 0xffffffffu : 0u);
    float2 floatValue155 =
        (float2(asfloat(0x3f800000u), asfloat(0x3f800000u)) + float2((-_ParticleBlendCoverage.x), (-_ParticleBlendCoverage.y)));
    uint wordValue156 = (comparisonMask154 != 0u ? 0x3f800000u : asuint(floatValue155.x));
    float floatValue157 = mad((-floatValue146), asfloat(wordValue156), asfloat(0x3f800000u));
    float floatValue158 = (floatValue146 * asfloat(wordValue156));
    float3 floatValue159 =
        mad(float3(floatValue106.x, floatValue106.y, floatValue106.z),
            float3(floatValue158, floatValue158, floatValue158), float3(floatValue157, floatValue157, floatValue157));
    float3 floatValue160 = (float3(floatValue158, floatValue158, floatValue158) *
                            float3(floatValue106.x, floatValue106.y, floatValue106.z));
    float dotProduct161 = dot(float3(floatValue106.x, floatValue106.y, floatValue106.z),
                              float3(asfloat(0x3e59c6edu), asfloat(0x3f371437u), asfloat(0x3d93d07du)));
    float floatValue162 = (floatValue158 * dotProduct161);
    uint comparisonMask163 = (asfloat(0x40000000u) == _ParticleBlendCoverage.y ? 0xffffffffu : 0u);
    uint3 wordValue164 = uint3((comparisonMask163 != 0u ? asuint(floatValue159.x) : asuint(floatValue160.x)),
                               (comparisonMask163 != 0u ? asuint(floatValue159.y) : asuint(floatValue160.y)),
                               (comparisonMask163 != 0u ? asuint(floatValue159.z) : asuint(floatValue160.z)));
    float dotProduct165 = dot(float3(asfloat(wordValue164.x), asfloat(wordValue164.y), asfloat(wordValue164.z)),
                              float3(asfloat(0x3e59c6edu), asfloat(0x3f371437u), asfloat(0x3d93d07du)));
    float3 floatValue166 = (float3((-dotProduct165), (-dotProduct165), (-dotProduct165)) +
                            float3(asfloat(wordValue164.x), asfloat(wordValue164.y), asfloat(wordValue164.z)));
    float3 floatValue167 = mad(float3(_ParticleOutputColorResponse.w, _ParticleOutputColorResponse.w, _ParticleOutputColorResponse.w),
                               float3(floatValue166.x, floatValue166.y, floatValue166.z),
                               float3(dotProduct165, dotProduct165, dotProduct165));
    float3 floatValue168 = (float3(floatValue167.x, floatValue167.y, floatValue167.z) *
                            float3(_ParticleOutputColorResponse.x, _ParticleOutputColorResponse.y, _ParticleOutputColorResponse.z));
    float floatValue169 = (asfloat(0x3f800000u) + (-_ParticleHighlightResponse.w));
    float3 floatValue170 = (float3(floatValue169, floatValue169, floatValue169) *
                            float3(asfloat(wordValue164.x), asfloat(wordValue164.y), asfloat(wordValue164.z)));
    o0.xyz = asuint(mad(float3(floatValue168.x, floatValue168.y, floatValue168.z),
                        float3(_ParticleHighlightResponse.w, _ParticleHighlightResponse.w, _ParticleHighlightResponse.w),
                        float3(floatValue170.x, floatValue170.y, floatValue170.z)));
    float floatValue171 = max(floatValue155.y, asfloat(0x00000000u));
    float floatValue172 = (floatValue155.y * floatValue158);
    o0.w = asuint((floatValue171 * floatValue158));
    float floatValue173 = max(floatValue172, floatValue162);
    float floatValue174 = saturate((floatValue173 * asfloat(0x41200000u)));
    uint comparisonMask175 = (asfloat(0x3f000000u) < floatValue174 ? 0xffffffffu : 0u);
    uint wordBits176 = (comparisonMask175 & 0x3f800000u);
    float floatValue177 = (_ParticleBlendCoverage.x * _ParticleBlendCoverage.z);
    o1.w = asuint((asfloat(wordBits176) * floatValue177));
    float floatValue178 = max(asfloat(v5.z), asfloat(0x322bcc77u));
    float2 quotientValue179 = (float2(asfloat(v5.x), asfloat(v5.y)) / float2(floatValue178, floatValue178));
    float floatValue180 = max(asfloat(v6.z), asfloat(0x322bcc77u));
    float2 quotientValue181 = (float2(asfloat(v6.x), asfloat(v6.y)) / float2(floatValue180, floatValue180));
    float2 floatValue182 =
        (float2((-quotientValue181.x), (-quotientValue181.y)) + float2(quotientValue179.x, quotientValue179.y));
    controlWords0.xyzw =
        uint4(asuint(floatValue182.x), asuint(floatValue182.y), asuint(quotientValue181.x), asuint(quotientValue181.y));
    controlWords1.xyzw =
        uint4(asuint(floatValue170.x), asuint(floatValue170.y), asuint(floatValue155.y), asuint(floatValue170.z));
    controlWords2.xyzw =
        uint4(asuint(floatValue168.x), asuint(floatValue168.y), asuint(floatValue168.z), asuint(floatValue125.w));
    controlWords3.xyzw =
        uint4(asuint(floatValue122.x), asuint(floatValue122.y), asuint(floatValue122.z), asuint(floatValue122.w));
    controlWords4.xyzw =
        uint4(asuint(floatValue73.x), asuint(floatValue73.y), asuint(floatValue73.z), asuint(floatValue73.w));
    controlWords5.xyzw =
        uint4(asuint(floatValue77.x), asuint(floatValue77.y), asuint(floatValue77.z), asuint(floatValue77.w));
    controlWords6.xyzw =
        uint4(asuint(floatValue76.x), asuint(floatValue76.y), asuint(floatValue76.z), asuint(floatValue76.w));

    float floatValue184 = (-asfloat(controlWords0.y));
    uint2 comparisonMask185 = uint2((asfloat(0x00000000u) < asfloat(controlWords0.x) ? 0xffffffffu : 0u),
                                    (asfloat(0x00000000u) < floatValue184 ? 0xffffffffu : 0u));
    uint2 comparisonMask186 = uint2((asfloat(controlWords0.x) < asfloat(0x00000000u) ? 0xffffffffu : 0u),
                                    (floatValue184 < asfloat(0x00000000u) ? 0xffffffffu : 0u));
    float2 floatValue187 = (float2(asfloat(controlWords0.x), asfloat(controlWords0.y)) *
                            float2(asfloat(0x3f000000u), asfloat(0xbf000000u)));
    float2 squareRoot188 = sqrt(float2(abs(floatValue187.x), abs(floatValue187.y)));
    float2 squareRoot189 = sqrt(float2(squareRoot188.x, squareRoot188.y));
    uint2 wordValue190 = (int2((-asint(comparisonMask185.x)), (-asint(comparisonMask185.y))) +
                          uint2(comparisonMask186.x, comparisonMask186.y));
    float2 floatValue191 = (float2)(int2(asint(wordValue190.x), asint(wordValue190.y)));
    float2 floatValue192 = (float2(floatValue191.x, floatValue191.y) * float2(squareRoot189.x, squareRoot189.y));
    float2 floatValue193 =
        mad(float2(floatValue192.x, floatValue192.y), float2(asfloat(0x3f000000u), asfloat(0x3f000000u)),
            float2(asfloat(0x3f000000u), asfloat(0x3f000000u)));
    float floatValue194 = ((-_ParticleBlendCoverage.x) + _ParticleBlendCoverage.w);
    float floatValue195 = saturate((floatValue194 + asfloat(0x3f800000u)));
    uint comparisonMask196 = (asfloat(0x3f000000u) < floatValue195 ? 0xffffffffu : 0u);
    uint2 wordBits197 =
        (uint2(asuint(floatValue193.x), asuint(floatValue193.y)) & uint2(comparisonMask196, comparisonMask196));
    o1.xy = asuint(min(float2(asfloat(wordBits197.x), asfloat(wordBits197.y)),
                       float2(asfloat(0x3f800000u), asfloat(0x3f800000u))));
    // mov o1.z, l(0x3f800000)
    o1.z = 0x3f800000u;
    // 输出边界只恢复源通道的浮点视图；位载体在这里按原SV_Target/SV_Depth接口写出。
    _output0 = asfloat(o0.xyzw);
    _output1 = asfloat(o1.xyzw);
    controlWords0.xyzw = uint4(wordBits197.x, wordBits197.y, comparisonMask196, asuint(floatValue191.y));
    controlWords1.xy = uint2(comparisonMask185.x, comparisonMask185.y);
    return;
}
