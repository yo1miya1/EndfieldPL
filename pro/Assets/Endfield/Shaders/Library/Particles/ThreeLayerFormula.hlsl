// 运行只接收语义材质、Unity矩阵与实时纹理；uint载体保留源算式跨分支位值。
// 带时间UV的分层表面的实际计算体；输入由Bindings和Geometry适配，输出保持源片元通道布局。
// uint载体保留寄存器位与掩码；asfloat/asuint不是数值转换，跨分支活跃分量不能提前覆盖。

// Character fragment graph: LayeredTimeUvSurface.
// Inputs: original interpolants and adapter-declared CB/resource slots.
// Intermediate float values are numeric; Words/masks retain raw 32-bit payloads.
// controlWords/controlValues carry live lanes across the original branch/loop edges.
// Samples, discard and output stores remain at their original control-flow positions.
void EFParticleEvaluateThreeLayer(float4 _input0 : SV_Position0, float4 _input1 : TEXCOORD0,
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
    uint4 controlWords4 = 0u;
    uint4 controlWords5 = 0u;
    uint4 controlWords6 = 0u;
    uint4 controlWords7 = 0u;
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
    float floatValue0 = mad((-_ParticleLayerInfluence.x), _ParticleLayerInfluence.y, asfloat(0x3f800000u));
    uint wordValue1 = 0x3f800000u;
    float floatValue2 = trunc(_ParticleMaskSampling.x);
    uint wordValue3 = 0x3f800000u;
    float floatValue4 = trunc(_ParticleNoiseSampling.x);
    float2 floatValue5 = (float2(floatValue2, floatValue4) + float2(asfloat(asuint(float4(_ParticleMipBias,0,0,0)).x), asfloat(asuint(float4(_ParticleMipBias,0,0,0)).x)));
    // 阶段：噪声层，驱动UV扭曲与覆盖率。
    // _ParticleNoiseMap：带原mip偏置采样，偏置与当前UV计算属于同一输入路径。
    float4 _sample0 =
        _ParticleNoiseMap.SampleBias(sampler_ParticleLinearRepeat, float2(asfloat(v2.x), asfloat(v2.y)), floatValue5.y);
    float4 sampledValue6 = _sample0.xyzw;
    uint wordValue7 = asuint(sampledValue6.x);
    float4 floatValue8 = (float4(asfloat(wordValue3), asfloat(wordValue3), asfloat(wordValue3), asfloat(wordValue7)) +
                          float4((-sampledValue6.x), (-sampledValue6.y), (-sampledValue6.z), (-sampledValue6.w)));
    float4 floatValue9 = mad(float4(_ParticleNoiseSampling.z, _ParticleNoiseSampling.z, _ParticleNoiseSampling.z, _ParticleNoiseSampling.z),
                             float4(floatValue8.x, floatValue8.y, floatValue8.z, floatValue8.w),
                             float4(sampledValue6.x, sampledValue6.y, sampledValue6.z, sampledValue6.w));
    float3 floatValue10 = (float3(asfloat(0x3f800000u), asfloat(0x3f800000u), asfloat(0x3f800000u)) +
                           float3((-_ParticleLayerInfluence.x), (-_ParticleLayerInfluence.z), (-_ParticleLayerInfluence.w)));
    float4 floatValue11 = mad(float4(floatValue9.x, floatValue9.y, floatValue9.w, floatValue9.x),
                              float4(_ParticleNoiseResponse.x, _ParticleNoiseResponse.x, _ParticleNoiseResponse.x, _ParticleNoiseResponse.y),
                              float4(floatValue10.x, floatValue10.x, floatValue10.x, floatValue10.y));
    float4 floatValue12 = mad(float4(floatValue9.x, floatValue9.y, floatValue9.z, floatValue9.w),
                              float4(_ParticleNoiseResponse.z, _ParticleNoiseResponse.z, _ParticleNoiseResponse.z, _ParticleNoiseResponse.z),
                              float4(floatValue10.z, floatValue10.z, floatValue10.z, floatValue10.z));
    float floatValue13 = (asfloat(0x3f800000u) + _ParticleDistortionMode.w);
    float floatValue14 = mad(floatValue11.x, floatValue13, (-_ParticleDistortionMode.w));
    float floatValue15 = (floatValue14 * floatValue11.z);
    float2 floatValue16 = (float2(floatValue14, floatValue14) * float2(_ParticleDistortionScale.x, _ParticleDistortionScale.y));
    float2 floatValue17 = mad(float2(floatValue15, floatValue11.y), float2(asfloat(0x40000000u), asfloat(0x40000000u)),
                              float2(asfloat(0xbf800000u), asfloat(0xbf800000u)));
    float2 floatValue18 = (float2(floatValue17.x, floatValue17.y) * float2(_ParticleDistortionScale.x, _ParticleDistortionScale.x));
    uint2 comparisonMask19 = uint2((asfloat(0x00000000u) != _ParticleDistortionMode.z ? 0xffffffffu : 0u),
                                   (asfloat(0x00000000u) != _ParticleDistortionMode.y ? 0xffffffffu : 0u));
    uint wordValue20 = (comparisonMask19.x != 0u ? v1.w : 0x3f800000u);
    float2 floatValue21 = (float2(asfloat(wordValue20), asfloat(wordValue20)) * float2(floatValue18.x, floatValue18.y));
    float2 floatValue22 = (float2(asfloat(wordValue20), asfloat(wordValue20)) * float2(floatValue16.x, floatValue16.y));
    uint2 comparisonMask23 = uint2((asfloat(0x00000000u) != _ParticleDistortionFlags.x ? 0xffffffffu : 0u),
                                   (asfloat(0x00000000u) != _ParticleDistortionFlags.y ? 0xffffffffu : 0u));
    uint2 wordValue24 = uint2((comparisonMask23.x != 0u ? asuint(floatValue21.x) : asuint(floatValue22.x)),
                              (comparisonMask23.x != 0u ? asuint(floatValue21.y) : asuint(floatValue22.y)));
    uint comparisonMask25 = (asfloat(0x00000000u) != _ParticleNoiseResponse.x ? 0xffffffffu : 0u);
    uint2 wordBits26 = (uint2(wordValue24.x, wordValue24.y) & uint2(comparisonMask25, comparisonMask25));
    float2 floatValue27 = mad(float2(asfloat(wordBits26.x), asfloat(wordBits26.y)),
                              float2(_ParticleMaskSampling.y, _ParticleMaskSampling.y), float2(asfloat(v2.z), asfloat(v2.w)));
    // 阶段：遮罩层，形成边缘与覆盖率。
    // _ParticleMaskMap：带原mip偏置采样，偏置与当前UV计算属于同一输入路径。
    float4 _sample1 =
        _ParticleMaskMap.SampleBias(sampler_ParticleLinearClamp, float2(floatValue27.x, floatValue27.y), floatValue5.x);
    float4 sampledValue28 = _sample1.xyzw;
    uint wordValue29 = asuint(sampledValue28.x);
    float4 floatValue30 = (float4(asfloat(wordValue1), asfloat(wordValue1), asfloat(wordValue1), asfloat(wordValue29)) +
                           float4((-sampledValue28.x), (-sampledValue28.y), (-sampledValue28.z), (-sampledValue28.w)));
    float4 floatValue31 = mad(float4(_ParticleMaskSampling.z, _ParticleMaskSampling.z, _ParticleMaskSampling.z, _ParticleMaskSampling.z),
                              float4(floatValue30.x, floatValue30.y, floatValue30.z, floatValue30.w),
                              float4(sampledValue28.x, sampledValue28.y, sampledValue28.z, sampledValue28.w));
    float3 floatValue32 = mad(float3(floatValue31.x, floatValue31.y, floatValue31.w),
                              float3(_ParticleMaskResponse.x, _ParticleMaskResponse.x, _ParticleMaskResponse.x),
                              float3(floatValue0, floatValue0, floatValue0));
    float floatValue33 = mad(floatValue32.x, floatValue13, (-_ParticleDistortionMode.w));
    float floatValue34 = (floatValue33 * floatValue32.z);
    float2 floatValue35 = (float2(floatValue33, floatValue33) * float2(_ParticleDistortionScale.z, _ParticleDistortionScale.w));
    float2 floatValue36 =
        mad(float2(floatValue35.x, floatValue35.y), float2(asfloat(wordValue20), asfloat(wordValue20)),
            float2(asfloat(wordBits26.x), asfloat(wordBits26.y)));
    float2 floatValue37 = mad(float2(floatValue34, floatValue32.y), float2(asfloat(0x40000000u), asfloat(0x40000000u)),
                              float2(asfloat(0xbf800000u), asfloat(0xbf800000u)));
    float2 floatValue38 = (float2(floatValue37.x, floatValue37.y) * float2(_ParticleDistortionScale.z, _ParticleDistortionScale.z));
    float2 floatValue39 =
        mad(float2(floatValue38.x, floatValue38.y), float2(asfloat(wordValue20), asfloat(wordValue20)),
            float2(asfloat(wordBits26.x), asfloat(wordBits26.y)));
    uint2 wordValue40 = uint2((comparisonMask23.y != 0u ? asuint(floatValue39.x) : asuint(floatValue36.x)),
                              (comparisonMask23.y != 0u ? asuint(floatValue39.y) : asuint(floatValue36.y)));
    uint comparisonMask41 = (asfloat(0x00000000u) != _ParticleMaskResponse.x ? 0xffffffffu : 0u);
    uint2 wordValue42 = uint2((comparisonMask41 != 0u ? wordValue40.x : wordBits26.x),
                              (comparisonMask41 != 0u ? wordValue40.y : wordBits26.y));
    float floatValue43 = mad(floatValue31.x, _ParticleMaskResponse.y, floatValue11.w);
    float floatValue44 = (_ParticleMaskResponse.y * _ParticleDistortionFlags.w);
    float floatValue45 = (floatValue44 * _ParticleDistortionFlags.z);
    float floatValue46 = mad((-floatValue44), _ParticleDistortionFlags.z, asfloat(0x3f800000u));
    float floatValue47 = mad(floatValue43, floatValue45, floatValue46);
    float2 floatValue48 = (float2(floatValue47, floatValue47) * float2(asfloat(wordValue42.x), asfloat(wordValue42.y)));
    float2 floatValue49 = mad(float2(floatValue48.x, floatValue48.y), float2(_ParticlePrimarySampling.x, _ParticlePrimarySampling.x),
                              float2(asfloat(v1.x), asfloat(v1.y)));
    float floatValue50 = trunc(_ParticlePrimarySampling.z);
    float floatValue51 = (floatValue50 + asfloat(asuint(float4(_ParticleMipBias,0,0,0)).x));
    // 阶段：主颜色层与UV采样。
    // _ParticleBaseMap：带原mip偏置采样，偏置与当前UV计算属于同一输入路径。
    float4 _sample2 =
        _ParticleBaseMap.SampleBias(sampler_ParticleLinearClamp, float2(floatValue49.x, floatValue49.y), floatValue51);
    float4 sampledValue52 = _sample2.xyzw;
    uint wordValue53 = asuint(sampledValue52.x);
    uint wordValue54 = 0x3f800000u;
    float4 floatValue55 =
        (float4((-sampledValue52.x), (-sampledValue52.y), (-sampledValue52.z), (-sampledValue52.w)) +
         float4(asfloat(wordValue54), asfloat(wordValue54), asfloat(wordValue54), asfloat(wordValue53)));
    float4 floatValue56 = mad(float4(_ParticlePrimarySampling.y, _ParticlePrimarySampling.y, _ParticlePrimarySampling.y, _ParticlePrimarySampling.y),
                              float4(floatValue55.x, floatValue55.y, floatValue55.z, floatValue55.w),
                              float4(sampledValue52.x, sampledValue52.y, sampledValue52.z, sampledValue52.w));
    uint comparisonMask57 = (asfloat(0x00000000u) != _ParticleColorStreamControls.y ? 0xffffffffu : 0u);
    uint4 wordValue58 =
        uint4((comparisonMask57 != 0u ? 0x3f800000u : v3.x), (comparisonMask57 != 0u ? 0x3f800000u : v3.y),
              (comparisonMask57 != 0u ? 0x3f800000u : v3.z), (comparisonMask57 != 0u ? 0x3f800000u : v3.w));
    float4 floatValue59 =
        (float4(asfloat(wordValue58.x), asfloat(wordValue58.y), asfloat(wordValue58.z), asfloat(wordValue58.w)) *
         float4(_ParticlePrimaryTint.x, _ParticlePrimaryTint.y, _ParticlePrimaryTint.z, _ParticlePrimaryTint.w));
    float4 floatValue60 = (float4(floatValue59.x, floatValue59.y, floatValue59.z, floatValue59.w) *
                           float4(_ParticleColorStreamControls.z, _ParticleColorStreamControls.z, _ParticleColorStreamControls.z, _ParticleColorStreamControls.w));
    float4 floatValue61 = (float4(floatValue56.x, floatValue56.y, floatValue56.z, floatValue56.w) *
                           float4(floatValue60.x, floatValue60.y, floatValue60.z, floatValue60.w));
    float4 floatValue62 = mad(float4(floatValue31.x, floatValue31.y, floatValue31.z, floatValue31.w),
                              float4(_ParticleMaskResponse.z, _ParticleMaskResponse.z, _ParticleMaskResponse.z, _ParticleMaskResponse.z),
                              float4(floatValue12.x, floatValue12.y, floatValue12.z, floatValue12.w));
    float4 floatValue63 = (float4(floatValue31.x, floatValue31.y, floatValue31.z, floatValue31.w) *
                           float4(_ParticleMaskResponse.w, _ParticleMaskResponse.w, _ParticleMaskResponse.w, _ParticleMaskResponse.w));
    float4 floatValue64 = mad(float4(floatValue9.x, floatValue9.y, floatValue9.z, floatValue9.w),
                              float4(_ParticleNoiseResponse.w, _ParticleNoiseResponse.w, _ParticleNoiseResponse.w, _ParticleNoiseResponse.w),
                              float4(floatValue63.x, floatValue63.y, floatValue63.z, floatValue63.w));
    float floatValue65 = mad(floatValue61.w, floatValue62.w, floatValue64.w);
    float4 floatValue66 = (float4(floatValue61.x, floatValue61.y, floatValue61.z, floatValue61.w) *
                           float4(floatValue62.x, floatValue62.y, floatValue62.z, floatValue62.w));
    float floatValue67 = saturate((floatValue65 * _ParticleSecondaryDistortionMode.w));
    float3 floatValue68 =
        (float3(floatValue67, floatValue67, floatValue67) * float3(floatValue64.x, floatValue64.y, floatValue64.z));
    float3 floatValue69 = mad(float3(floatValue68.x, floatValue68.y, floatValue68.z),
                              float3(_ParticleSecondaryDistortionMode.x, _ParticleSecondaryDistortionMode.y, _ParticleSecondaryDistortionMode.z),
                              float3(floatValue66.x, floatValue66.y, floatValue66.z));
    float floatValue70 = (_ParticleDistortionFlags.w * _ParticleSoftIntersection.w);
    float floatValue71 = mad((-_ParticleDistortionFlags.w), _ParticleSoftIntersection.w, asfloat(0x3f800000u));
    float floatValue72 = mad(floatValue43, floatValue70, floatValue71);
    float floatValue73 = (asfloat(v1.z) + _ParticleSoftIntersection.y);
    float floatValue74 = mad(floatValue73, asfloat(0x400147aeu), asfloat(0xbc23d700u));
    float floatValue75 = mad(floatValue72, floatValue74, asfloat(0xbf800000u));
    float floatValue76 = mad(floatValue31.x, _ParticleMaskCoverage.x, (-floatValue75));
    float floatValue77 = ((-floatValue76) + _ParticleSoftIntersection.z);
    float floatValue78 = saturate((floatValue76 * _ParticleSoftIntersection.x));
    float floatValue79 = (floatValue78 * floatValue66.w);
    uint wordValue80 = (comparisonMask19.y != 0u ? asuint(floatValue79) : asuint(floatValue66.w));
    float floatValue81 = saturate((floatValue77 * _ParticleSoftIntersection.x));
    float3 floatValue82 = (float3(floatValue81, floatValue81, floatValue81) *
                           float3(_ParticleSecondaryDistortionScale.x, _ParticleSecondaryDistortionScale.y, _ParticleSecondaryDistortionScale.z));
    float3 floatValue83 = mad(float3(floatValue82.x, floatValue82.y, floatValue82.z),
                              float3(_ParticleColorStreamControls.z, _ParticleColorStreamControls.z, _ParticleColorStreamControls.z),
                              float3((-floatValue69.x), (-floatValue69.y), (-floatValue69.z)));
    float3 floatValue84 =
        mad(float3(floatValue81, floatValue81, floatValue81), float3(floatValue83.x, floatValue83.y, floatValue83.z),
            float3(floatValue69.x, floatValue69.y, floatValue69.z));
    uint3 wordValue85 = uint3((comparisonMask19.y != 0u ? asuint(floatValue84.x) : asuint(floatValue69.x)),
                              (comparisonMask19.y != 0u ? asuint(floatValue84.y) : asuint(floatValue69.y)),
                              (comparisonMask19.y != 0u ? asuint(floatValue84.z) : asuint(floatValue69.z)));
    float3 floatValue86 = (float3(asfloat(wordValue85.x), asfloat(wordValue85.y), asfloat(wordValue85.z)) +
                           float3((-_ParticleHighlightResponse.y), (-_ParticleHighlightResponse.y), (-_ParticleHighlightResponse.y)));
    float3 floatValue87 = max(float3(floatValue86.x, floatValue86.y, floatValue86.z),
                              float3(asfloat(0x00000000u), asfloat(0x00000000u), asfloat(0x00000000u)));
    float3 floatValue88 = mad(float3(floatValue87.x, floatValue87.y, floatValue87.z),
                              float3(_ParticleHighlightResponse.z, _ParticleHighlightResponse.z, _ParticleHighlightResponse.z),
                              float3(asfloat(wordValue85.x), asfloat(wordValue85.y), asfloat(wordValue85.z)));
    float floatValue89 = (asfloat(0x3f800000u) + (-_ParticleExposureViewControls.x));
    float floatValue90 = mad(asfloat(asuint(float4(1,_EndfieldSceneExposure,_ScreenParams.x/_ScreenParams.y,0)).y), _ParticleExposureViewControls.x, floatValue89);
    float3 floatValue91 =
        (float3(floatValue88.x, floatValue88.y, floatValue88.z) * float3(floatValue90, floatValue90, floatValue90));
    float3 floatValue92 = max(float3(floatValue91.x, floatValue91.y, floatValue91.z),
                              float3(asfloat(0x00000000u), asfloat(0x00000000u), asfloat(0x00000000u)));
    float3 floatValue93 = min(float3(floatValue92.x, floatValue92.y, floatValue92.z),
                              float3(asfloat(0x447a0000u), asfloat(0x447a0000u), asfloat(0x447a0000u)));
    uint2 wordValue94 = (uint2)(float2(asfloat(v0.x), asfloat(v0.y)));
    float2 floatValue95 = (float2)(uint2(wordValue94.x, wordValue94.y));
    float2 floatValue96 = (float2(floatValue95.x, floatValue95.y) * float2(asfloat(asuint(float4(_ScreenParams.xy,rcp(_ScreenParams.xy))).z), asfloat(asuint(float4(_ScreenParams.xy,rcp(_ScreenParams.xy))).w)));
    float2 floatValue97 =
        mad(float2(floatValue96.x, floatValue96.y), float2(asfloat(0x40000000u), asfloat(0x40000000u)),
            float2(asfloat(0xbf800000u), asfloat(0xbf800000u)));
    float4 floatValue98 = (float4((-floatValue97.y), (-floatValue97.y), (-floatValue97.y), (-floatValue97.y)) *
                           float4(asfloat(EFParticleInverseViewColumn(1).x), asfloat(EFParticleInverseViewColumn(1).y), asfloat(EFParticleInverseViewColumn(1).z), asfloat(EFParticleInverseViewColumn(1).w)));
    float4 floatValue99 = mad(float4(asfloat(EFParticleInverseViewColumn(0).x), asfloat(EFParticleInverseViewColumn(0).y), asfloat(EFParticleInverseViewColumn(0).z), asfloat(EFParticleInverseViewColumn(0).w)),
                              float4(floatValue97.x, floatValue97.x, floatValue97.x, floatValue97.x),
                              float4(floatValue98.x, floatValue98.y, floatValue98.z, floatValue98.w));
    float2 floatValue100 = (float2(asfloat(v0.x), asfloat(v0.y)) * float2(asfloat(asuint(float4(_ScreenParams.xy,rcp(_ScreenParams.xy))).z), asfloat(asuint(float4(_ScreenParams.xy,rcp(_ScreenParams.xy))).w)));
    // 阶段：当前opaque深度，计算软交界。
    // _CameraDepthTexture：显式LOD采样，不能改成依赖屏幕导数的隐式LOD。
    float4 _sample3 = _CameraDepthTexture.SampleLevel(sampler_ParticlePointClamp, float2(floatValue100.x, floatValue100.y),
                                         asfloat(0x00000000u));
    float sampledValue101 = _sample3.x;
    float2 floatValue102 =
        mad(float2(floatValue100.x, floatValue100.y), float2(asfloat(0x40000000u), asfloat(0x40000000u)),
            float2(asfloat(0xbf800000u), asfloat(0xbf800000u)));
    float4 floatValue103 = mad(float4(asfloat(EFParticleInverseViewColumn(2).x), asfloat(EFParticleInverseViewColumn(2).y), asfloat(EFParticleInverseViewColumn(2).z), asfloat(EFParticleInverseViewColumn(2).w)),
                               float4(sampledValue101, sampledValue101, sampledValue101, sampledValue101),
                               float4(floatValue99.x, floatValue99.y, floatValue99.z, floatValue99.w));
    float4 floatValue104 = (float4(floatValue103.x, floatValue103.y, floatValue103.z, floatValue103.w) +
                            float4(asfloat(EFParticleInverseViewColumn(3).x), asfloat(EFParticleInverseViewColumn(3).y), asfloat(EFParticleInverseViewColumn(3).z), asfloat(EFParticleInverseViewColumn(3).w)));
    float3 quotientValue105 = (float3(floatValue104.x, floatValue104.y, floatValue104.z) /
                               float3(floatValue104.w, floatValue104.w, floatValue104.w));
    float floatValue106 = (quotientValue105.y * asfloat(EFParticleViewColumn(1).z));
    float floatValue107 = mad(asfloat(EFParticleViewColumn(0).z), quotientValue105.x, floatValue106);
    float floatValue108 = mad(asfloat(EFParticleViewColumn(2).z), quotientValue105.z, floatValue107);
    float4 floatValue109 = (float4((-floatValue102.y), (-floatValue102.y), (-floatValue102.y), (-floatValue102.y)) *
                            float4(asfloat(EFParticleInverseViewColumn(1).x), asfloat(EFParticleInverseViewColumn(1).y), asfloat(EFParticleInverseViewColumn(1).z), asfloat(EFParticleInverseViewColumn(1).w)));
    float4 floatValue110 = mad(float4(asfloat(EFParticleInverseViewColumn(0).x), asfloat(EFParticleInverseViewColumn(0).y), asfloat(EFParticleInverseViewColumn(0).z), asfloat(EFParticleInverseViewColumn(0).w)),
                               float4(floatValue102.x, floatValue102.x, floatValue102.x, floatValue102.x),
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
    float2 floatValue117 = (float2(floatValue108, floatValue116) + float2(asfloat(EFParticleViewColumn(3).z), asfloat(EFParticleViewColumn(3).z)));
    float floatValue118 = ((-abs(floatValue117.y)) + abs(floatValue117.x));
    float2 floatValue119 =
        (float2(abs(floatValue117.y), abs(floatValue117.y)) + float2((-_ParticleDepthFadeFar.y), (-_ParticleDepthFadeFar.w)));
    float floatValue120 = (floatValue118 + _ParticleDepthFadeNear.y);
    float quotientValue121 = saturate((floatValue120 / _ParticleDepthFadeNear.x));
    float floatValue122 = (asfloat(wordValue80) * quotientValue121);
    float floatValue123 = ((-_ParticleDepthFadeFar.y) + _ParticleDepthFadeFar.z);
    float quotientValue124 = saturate((floatValue119.x / floatValue123));
    float floatValue125 = ((-_ParticleDepthFadeFar.w) + _ParticleOutputTint.x);
    float quotientValue126 = saturate((floatValue119.y / floatValue125));
    float floatValue127 = (quotientValue126 * quotientValue124);
    uint comparisonMask128 = (asfloat(0x00000000u) != _ParticleDepthFadeFar.x ? 0xffffffffu : 0u);
    uint wordValue129 = (comparisonMask128 != 0u ? asuint(floatValue127) : 0x3f800000u);
    float floatValue130 = saturate((floatValue122 * asfloat(wordValue129)));
    uint wordBits131 = (v6.x << (0x00000004u & 31u));
    float floatValue132 = (asfloat(0x3f800000u) + (-_ParticleInstanceCoverage.y));
    float floatValue133 = (floatValue130 * floatValue132);
    float dotProduct134 = dot(float2(asfloat(v0.x), asfloat(v0.y)), float2(asfloat(0x3d897143u), asfloat(0x3bbf4590u)));
    float floatValue135 = frac(dotProduct134);
    float floatValue136 = (floatValue135 * asfloat(0x4253ee82u));
    float floatValue137 = frac(floatValue136);
    uint comparisonMask138 = (_ParticleInstanceCoverage.x >= asfloat(0x00000000u) ? 0xffffffffu : 0u);
    uint wordValue139 = (comparisonMask138 != 0u ? asuint(floatValue137) : asuint((-floatValue137)));
    float floatValue140 = ((-asfloat(wordValue139)) + _ParticleInstanceCoverage.x);
    uint comparisonMask141 = (asfloat(0x00000000u) < floatValue140 ? 0xffffffffu : 0u);
    float2 floatValue142 =
        (float2(asfloat(0x3f800000u), asfloat(0x3f800000u)) + float2((-_ParticleBlendCoverage.x), (-_ParticleBlendCoverage.y)));
    uint wordValue143 = (comparisonMask141 != 0u ? 0x3f800000u : asuint(floatValue142.x));
    float floatValue144 = mad((-floatValue133), asfloat(wordValue143), asfloat(0x3f800000u));
    float floatValue145 = (floatValue133 * asfloat(wordValue143));
    float3 floatValue146 =
        mad(float3(floatValue93.x, floatValue93.y, floatValue93.z), float3(floatValue145, floatValue145, floatValue145),
            float3(floatValue144, floatValue144, floatValue144));
    float3 floatValue147 =
        (float3(floatValue145, floatValue145, floatValue145) * float3(floatValue93.x, floatValue93.y, floatValue93.z));
    float dotProduct148 = dot(float3(floatValue93.x, floatValue93.y, floatValue93.z),
                              float3(asfloat(0x3e59c6edu), asfloat(0x3f371437u), asfloat(0x3d93d07du)));
    float floatValue149 = (floatValue145 * dotProduct148);
    uint comparisonMask150 = (asfloat(0x40000000u) == _ParticleBlendCoverage.y ? 0xffffffffu : 0u);
    uint3 wordValue151 = uint3((comparisonMask150 != 0u ? asuint(floatValue146.x) : asuint(floatValue147.x)),
                               (comparisonMask150 != 0u ? asuint(floatValue146.y) : asuint(floatValue147.y)),
                               (comparisonMask150 != 0u ? asuint(floatValue146.z) : asuint(floatValue147.z)));
    float dotProduct152 = dot(float3(asfloat(wordValue151.x), asfloat(wordValue151.y), asfloat(wordValue151.z)),
                              float3(asfloat(0x3e59c6edu), asfloat(0x3f371437u), asfloat(0x3d93d07du)));
    float3 floatValue153 = (float3((-dotProduct152), (-dotProduct152), (-dotProduct152)) +
                            float3(asfloat(wordValue151.x), asfloat(wordValue151.y), asfloat(wordValue151.z)));
    float3 floatValue154 = mad(float3(_ParticleOutputColorResponse.w, _ParticleOutputColorResponse.w, _ParticleOutputColorResponse.w),
                               float3(floatValue153.x, floatValue153.y, floatValue153.z),
                               float3(dotProduct152, dotProduct152, dotProduct152));
    float3 floatValue155 = (float3(floatValue154.x, floatValue154.y, floatValue154.z) *
                            float3(_ParticleOutputColorResponse.x, _ParticleOutputColorResponse.y, _ParticleOutputColorResponse.z));
    float floatValue156 = (asfloat(0x3f800000u) + (-_ParticleHighlightResponse.w));
    float3 floatValue157 = (float3(floatValue156, floatValue156, floatValue156) *
                            float3(asfloat(wordValue151.x), asfloat(wordValue151.y), asfloat(wordValue151.z)));
    o0.xyz = asuint(mad(float3(floatValue155.x, floatValue155.y, floatValue155.z),
                        float3(_ParticleHighlightResponse.w, _ParticleHighlightResponse.w, _ParticleHighlightResponse.w),
                        float3(floatValue157.x, floatValue157.y, floatValue157.z)));
    float floatValue158 = max(floatValue142.y, asfloat(0x00000000u));
    float floatValue159 = (floatValue142.y * floatValue145);
    o0.w = asuint((floatValue158 * floatValue145));
    float floatValue160 = max(floatValue159, floatValue149);
    float floatValue161 = saturate((floatValue160 * asfloat(0x41200000u)));
    uint comparisonMask162 = (asfloat(0x3f000000u) < floatValue161 ? 0xffffffffu : 0u);
    uint wordBits163 = (comparisonMask162 & 0x3f800000u);
    float floatValue164 = (_ParticleBlendCoverage.x * _ParticleBlendCoverage.z);
    o1.w = asuint((asfloat(wordBits163) * floatValue164));
    float floatValue165 = max(asfloat(v4.z), asfloat(0x322bcc77u));
    float2 quotientValue166 = (float2(asfloat(v4.x), asfloat(v4.y)) / float2(floatValue165, floatValue165));
    float floatValue167 = max(asfloat(v5.z), asfloat(0x322bcc77u));
    float2 quotientValue168 = (float2(asfloat(v5.x), asfloat(v5.y)) / float2(floatValue167, floatValue167));
    float2 floatValue169 =
        (float2((-quotientValue168.x), (-quotientValue168.y)) + float2(quotientValue166.x, quotientValue166.y));
    controlWords0.xyzw =
        uint4(asuint(floatValue169.x), asuint(floatValue169.y), asuint(quotientValue168.x), asuint(quotientValue168.y));
    controlWords1.xyzw =
        uint4(asuint(floatValue157.x), asuint(floatValue157.y), asuint(floatValue142.y), asuint(floatValue157.z));
    controlWords2.xyzw =
        uint4(asuint(floatValue155.x), asuint(floatValue155.y), asuint(floatValue155.z), asuint(floatValue112.w));
    controlWords3.xyzw =
        uint4(asuint(floatValue109.x), asuint(floatValue109.y), asuint(floatValue109.z), asuint(floatValue109.w));
    controlWords4.xyzw =
        uint4(asuint(floatValue63.x), asuint(floatValue63.y), asuint(floatValue63.z), asuint(floatValue63.w));
    controlWords5.xyz = uint3(comparisonMask23.x, comparisonMask19.y, comparisonMask23.y);
    controlWords6.xyzw =
        uint4(asuint(floatValue31.x), asuint(floatValue31.y), asuint(floatValue31.z), asuint(floatValue31.w));
    controlWords7.xyzw =
        uint4(asuint(floatValue34), asuint(floatValue32.x), asuint(floatValue32.y), asuint(floatValue32.z));

    float floatValue171 = (-asfloat(controlWords0.y));
    uint2 comparisonMask172 = uint2((asfloat(0x00000000u) < asfloat(controlWords0.x) ? 0xffffffffu : 0u),
                                    (asfloat(0x00000000u) < floatValue171 ? 0xffffffffu : 0u));
    uint2 comparisonMask173 = uint2((asfloat(controlWords0.x) < asfloat(0x00000000u) ? 0xffffffffu : 0u),
                                    (floatValue171 < asfloat(0x00000000u) ? 0xffffffffu : 0u));
    float2 floatValue174 = (float2(asfloat(controlWords0.x), asfloat(controlWords0.y)) *
                            float2(asfloat(0x3f000000u), asfloat(0xbf000000u)));
    float2 squareRoot175 = sqrt(float2(abs(floatValue174.x), abs(floatValue174.y)));
    float2 squareRoot176 = sqrt(float2(squareRoot175.x, squareRoot175.y));
    uint2 wordValue177 = (int2((-asint(comparisonMask172.x)), (-asint(comparisonMask172.y))) +
                          uint2(comparisonMask173.x, comparisonMask173.y));
    float2 floatValue178 = (float2)(int2(asint(wordValue177.x), asint(wordValue177.y)));
    float2 floatValue179 = (float2(floatValue178.x, floatValue178.y) * float2(squareRoot176.x, squareRoot176.y));
    float2 floatValue180 =
        mad(float2(floatValue179.x, floatValue179.y), float2(asfloat(0x3f000000u), asfloat(0x3f000000u)),
            float2(asfloat(0x3f000000u), asfloat(0x3f000000u)));
    float floatValue181 = ((-_ParticleBlendCoverage.x) + _ParticleBlendCoverage.w);
    float floatValue182 = saturate((floatValue181 + asfloat(0x3f800000u)));
    uint comparisonMask183 = (asfloat(0x3f000000u) < floatValue182 ? 0xffffffffu : 0u);
    uint2 wordBits184 =
        (uint2(asuint(floatValue180.x), asuint(floatValue180.y)) & uint2(comparisonMask183, comparisonMask183));
    o1.xy = asuint(min(float2(asfloat(wordBits184.x), asfloat(wordBits184.y)),
                       float2(asfloat(0x3f800000u), asfloat(0x3f800000u))));
    // mov o1.z, l(0x3f800000)
    o1.z = 0x3f800000u;
    // 输出边界只恢复源通道的浮点视图；位载体在这里按原SV_Target/SV_Depth接口写出。
    _output0 = asfloat(o0.xyzw);
    _output1 = asfloat(o1.xyzw);
    controlWords0.xyzw = uint4(wordBits184.x, wordBits184.y, comparisonMask183, asuint(floatValue178.y));
    controlWords1.xy = uint2(comparisonMask172.x, comparisonMask172.y);
    return;
}
