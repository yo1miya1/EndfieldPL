// 运行只接收语义材质、Unity矩阵与实时纹理；uint载体保留源算式跨分支位值。
// 顶点色表面的实际计算体；输入由Bindings和Geometry适配，输出保持源片元通道布局。
// uint载体保留寄存器位与掩码；asfloat/asuint不是数值转换，跨分支活跃分量不能提前覆盖。

// Character fragment graph: VertexColorSurface.
// Inputs: original interpolants and adapter-declared CB/resource slots.
// Intermediate float values are numeric; Words/masks retain raw 32-bit payloads.
// controlWords/controlValues carry live lanes across the original branch/loop edges.
// Samples, discard and output stores remain at their original control-flow positions.
void EFParticleEvaluateRefraction(float4 _input0 : SV_Position0, float2 _input1 : TEXCOORD0,
                                           float2 _input2 : TEXCOORD1, float4 _input3 : TEXCOORD2,
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
    uint4 o0 = 0u;
    uint4 o1 = 0u;
    // 把插值输入写入原寄存器载体；浮点值按位装入uint，整数及正反面掩码保留原类型。
    v0.xyzw = asuint(_input0);
    v1.xy = asuint(_input1);
    v1.zw = asuint(_input2);
    v2.xyzw = asuint(_input3);
    v3.xyz = asuint(_input4);
    v4.xyz = asuint(_input5);
    v5.x = _input6;
    float2 floatValue0 = mad(float2(_ParticleUvRotation.x, _ParticleUvRotation.y),
                             float2(asfloat(asuint(float4(0,0,0,_ParticlePhase+_Time.y*_ParticlePhaseSpeed)).w), asfloat(asuint(float4(0,0,0,_ParticlePhase+_Time.y*_ParticlePhaseSpeed)).w)), float2(asfloat(v1.x), asfloat(v1.y)));
    float2 floatValue1 = mad(float2(_ParticleUvRotation.z, _ParticleUvRotation.w), float2(asfloat(v1.z), asfloat(v1.z)),
                             float2(floatValue0.x, floatValue0.y));
    float2 floatValue2 = (float2(floatValue1.x, floatValue1.y) + float2(asfloat(0xbf000000u), asfloat(0xbf000000u)));
    float floatValue3 = (asfloat(0x3c8efa35u) * _ParticlePrimaryTint.x);
    float floatValue4 = sin(floatValue3);
    float floatValue5 = cos(floatValue3);
    uint wordValue6 = asuint(floatValue4);
    uint wordValue7 = asuint(floatValue5);
    float floatValue8 = (-floatValue4);
    float dotProduct9 = dot(float2(floatValue2.x, floatValue2.y), float2(floatValue8, asfloat(wordValue7)));
    float dotProduct10 = dot(float2(floatValue2.x, floatValue2.y), float2(asfloat(wordValue7), asfloat(wordValue6)));
    float2 floatValue11 = (float2(dotProduct10, dotProduct9) + float2(asfloat(0x3f000000u), asfloat(0x3f000000u)));
    float2 floatValue12 = mad(float2(floatValue11.x, floatValue11.y), float2(_ParticleUvVelocity.x, _ParticleUvVelocity.y),
                              float2(_ParticleUvVelocity.z, _ParticleUvVelocity.w));
    // 阶段：主颜色层与UV采样。
    // _ParticleBaseMap：带原mip偏置采样，偏置与当前UV计算属于同一输入路径。
    float4 _sample0 = _ParticleBaseMap.SampleBias(sampler_ParticleLinearRepeat, float2(floatValue12.x, floatValue12.y),
                                        asfloat(asuint(float4(_ParticleMipBias,0,0,0)).x));
    float3 sampledValue13 = _sample0.xyw;
    float floatValue14 = (asfloat(0x3f800000u) + _ParticleExposureViewControls.y);
    float floatValue15 = mad(sampledValue13.x, floatValue14, (-_ParticleExposureViewControls.y));
    float floatValue16 = (floatValue15 * sampledValue13.z);
    float2 floatValue17 =
        mad(float2(floatValue16, sampledValue13.y), float2(asfloat(0x40000000u), asfloat(0x40000000u)),
            float2(asfloat(0xbf800000u), asfloat(0xbf800000u)));
    float2 floatValue18 = (float2(floatValue15, floatValue15) * float2(_ParticlePrimarySampling.x, _ParticlePrimarySampling.y));
    uint wordBits19 = (v5.x << (0x00000004u & 31u));
    float floatValue20 = (asfloat(0x3f800000u) + (-_ParticleInstanceCoverage.y));
    float floatValue21 = (_ParticleHighlightResponse.w * _ParticleExposureViewControls.x);
    float floatValue22 = (floatValue20 * floatValue21);
    float floatValue23 = (floatValue22 * asfloat(v2.w));
    float4 floatValue24 = (float4(floatValue17.x, floatValue17.y, floatValue18.x, floatValue18.y) *
                           float4(floatValue23, floatValue23, floatValue23, floatValue23));
    float2 floatValue25 = mad(float2(floatValue24.x, floatValue24.y), float2(_ParticlePrimarySampling.x, _ParticlePrimarySampling.y),
                              float2((-floatValue24.z), (-floatValue24.w)));
    float2 floatValue26 = mad(float2(_ParticleHighlightResponse.z, _ParticleHighlightResponse.z), float2(floatValue25.x, floatValue25.y),
                              float2(floatValue24.z, floatValue24.w));
    float2 floatValue27 = mad(float2(_ParticleColorResponse.x, _ParticleColorResponse.y),
                              float2(asfloat(asuint(float4(0,0,0,_ParticlePhase+_Time.y*_ParticlePhaseSpeed)).w), asfloat(asuint(float4(0,0,0,_ParticlePhase+_Time.y*_ParticlePhaseSpeed)).w)), float2(asfloat(v1.x), asfloat(v1.y)));
    float2 floatValue28 = mad(float2(_ParticleColorResponse.z, _ParticleColorResponse.w), float2(asfloat(v1.w), asfloat(v1.w)),
                              float2(floatValue27.x, floatValue27.y));
    float2 floatValue29 = (float2(floatValue28.x, floatValue28.y) + float2(asfloat(0xbf000000u), asfloat(0xbf000000u)));
    float floatValue30 = (asfloat(0x3c8efa35u) * _ParticleUvWeights.x);
    float floatValue31 = sin(floatValue30);
    float floatValue32 = cos(floatValue31);
    uint wordValue33 = asuint(floatValue31);
    uint wordValue34 = asuint(floatValue32);
    float floatValue35 = (-floatValue31);
    float dotProduct36 = dot(float2(floatValue29.x, floatValue29.y), float2(floatValue35, asfloat(wordValue34)));
    float dotProduct37 =
        dot(float2(floatValue29.x, floatValue29.y), float2(asfloat(wordValue34), asfloat(wordValue33)));
    float2 floatValue38 = (float2(dotProduct37, dotProduct36) + float2(asfloat(0x3f000000u), asfloat(0x3f000000u)));
    float2 floatValue39 = mad(float2(floatValue38.x, floatValue38.y), float2(_ParticleUvTransform.x, _ParticleUvTransform.y),
                              float2(_ParticleUvTransform.z, _ParticleUvTransform.w));
    float2 floatValue40 = mad(float2(floatValue26.x, floatValue26.y), float2(_ParticleUvWeights.w, _ParticleUvWeights.w),
                              float2(floatValue39.x, floatValue39.y));
    float2 floatValue41 = mad(float2(asfloat(v0.x), asfloat(v0.y)), float2(asfloat(asuint(float4(_ScreenParams.xy,rcp(_ScreenParams.xy))).z), asfloat(asuint(float4(_ScreenParams.xy,rcp(_ScreenParams.xy))).w)),
                              float2(floatValue26.x, floatValue26.y));
    // 阶段：显式透明阶段快照，作为折射背景。
    // _CameraRefractionTexture：带原mip偏置采样，偏置与当前UV计算属于同一输入路径。
    float4 _sample1 = _CameraRefractionTexture.SampleBias(sampler_ParticleLinearClamp, float2(floatValue41.x, floatValue41.y),
                                        asfloat(asuint(float4(_ParticleMipBias,0,0,0)).x));
    float3 sampledValue42 = _sample1.xyz;
    // 阶段：遮罩层，形成边缘与覆盖率。
    // _ParticleMaskMap：带原mip偏置采样，偏置与当前UV计算属于同一输入路径。
    float4 _sample2 = _ParticleMaskMap.SampleBias(sampler_ParticleLinearClamp, float2(floatValue40.x, floatValue40.y),
                                        asfloat(asuint(float4(_ParticleMipBias,0,0,0)).x));
    float4 sampledValue43 = _sample2.xyzw;
    uint wordValue44 = asuint(sampledValue43.x);
    uint wordValue45 = 0x3f800000u;
    float4 floatValue46 =
        (float4((-sampledValue43.x), (-sampledValue43.y), (-sampledValue43.z), (-sampledValue43.w)) +
         float4(asfloat(wordValue45), asfloat(wordValue45), asfloat(wordValue45), asfloat(wordValue44)));
    float4 floatValue47 = mad(float4(_ParticleUvWeights.y, _ParticleUvWeights.y, _ParticleUvWeights.y, _ParticleUvWeights.y),
                              float4(floatValue46.x, floatValue46.y, floatValue46.z, floatValue46.w),
                              float4(sampledValue43.x, sampledValue43.y, sampledValue43.z, sampledValue43.w));
    uint wordValue48 = 0x3f800000u;
    float4 floatValue49 = (float4(floatValue47.x, floatValue47.y, floatValue47.z, floatValue47.w) *
                           float4(sampledValue42.x, sampledValue42.y, sampledValue42.z, asfloat(wordValue48)));
    float2 floatValue50 = (float2(asfloat(v0.x), asfloat(v0.y)) * float2(asfloat(asuint(float4(_ScreenParams.xy,rcp(_ScreenParams.xy))).z), asfloat(asuint(float4(_ScreenParams.xy,rcp(_ScreenParams.xy))).w)));
    float2 floatValue51 =
        mad(float2(floatValue50.x, floatValue50.y), float2(asfloat(0x40000000u), asfloat(0x40000000u)),
            float2(asfloat(0xbf800000u), asfloat(0xbf800000u)));
    float4 floatValue52 = (float4((-floatValue51.y), (-floatValue51.y), (-floatValue51.y), (-floatValue51.y)) *
                           float4(asfloat(EFParticleInverseViewColumn(1).x), asfloat(EFParticleInverseViewColumn(1).y), asfloat(EFParticleInverseViewColumn(1).z), asfloat(EFParticleInverseViewColumn(1).w)));
    float4 floatValue53 = mad(float4(asfloat(EFParticleInverseViewColumn(0).x), asfloat(EFParticleInverseViewColumn(0).y), asfloat(EFParticleInverseViewColumn(0).z), asfloat(EFParticleInverseViewColumn(0).w)),
                              float4(floatValue51.x, floatValue51.x, floatValue51.x, floatValue51.x),
                              float4(floatValue52.x, floatValue52.y, floatValue52.z, floatValue52.w));
    float4 floatValue54 = mad(float4(asfloat(EFParticleInverseViewColumn(2).x), asfloat(EFParticleInverseViewColumn(2).y), asfloat(EFParticleInverseViewColumn(2).z), asfloat(EFParticleInverseViewColumn(2).w)),
                              float4(asfloat(v0.z), asfloat(v0.z), asfloat(v0.z), asfloat(v0.z)),
                              float4(floatValue53.x, floatValue53.y, floatValue53.z, floatValue53.w));
    float4 floatValue55 = (float4(floatValue54.x, floatValue54.y, floatValue54.z, floatValue54.w) +
                           float4(asfloat(EFParticleInverseViewColumn(3).x), asfloat(EFParticleInverseViewColumn(3).y), asfloat(EFParticleInverseViewColumn(3).z), asfloat(EFParticleInverseViewColumn(3).w)));
    float3 quotientValue56 = (float3(floatValue55.x, floatValue55.y, floatValue55.z) /
                              float3(floatValue55.w, floatValue55.w, floatValue55.w));
    float floatValue57 = (quotientValue56.y * asfloat(EFParticleViewColumn(1).z));
    float floatValue58 = mad(asfloat(EFParticleViewColumn(0).z), quotientValue56.x, floatValue57);
    float floatValue59 = mad(asfloat(EFParticleViewColumn(2).z), quotientValue56.z, floatValue58);
    float floatValue60 = (floatValue59 + asfloat(EFParticleViewColumn(3).z));
    float2 floatValue61 =
        (float2(abs(floatValue60), abs(floatValue60)) + float2((-_ParticleBlendCoverage.y), (-_ParticleBlendCoverage.w)));
    float floatValue62 = ((-_ParticleBlendCoverage.y) + _ParticleBlendCoverage.z);
    float quotientValue63 = saturate((floatValue61.x / floatValue62));
    float floatValue64 = ((-_ParticleBlendCoverage.w) + _ParticleColorStreamControls.x);
    float quotientValue65 = saturate((floatValue61.y / floatValue64));
    float floatValue66 = (quotientValue65 * quotientValue63);
    uint comparisonMask67 = (asfloat(0x00000000u) != _ParticleBlendCoverage.x ? 0xffffffffu : 0u);
    uint wordValue68 = (comparisonMask67 != 0u ? asuint(floatValue66) : 0x3f800000u);
    o0.w = asuint(saturate((floatValue49.w * asfloat(wordValue68))));
    float3 floatValue69 = max(float3(floatValue49.x, floatValue49.y, floatValue49.z),
                              float3(asfloat(0x00000000u), asfloat(0x00000000u), asfloat(0x00000000u)));
    o0.xyz = asuint(min(float3(floatValue69.x, floatValue69.y, floatValue69.z),
                        float3(asfloat(0x447a0000u), asfloat(0x447a0000u), asfloat(0x447a0000u))));
    float floatValue70 = max(asfloat(v3.z), asfloat(0x322bcc77u));
    float2 quotientValue71 = (float2(asfloat(v3.x), asfloat(v3.y)) / float2(floatValue70, floatValue70));
    float floatValue72 = max(asfloat(v4.z), asfloat(0x322bcc77u));
    float2 quotientValue73 = (float2(asfloat(v4.x), asfloat(v4.y)) / float2(floatValue72, floatValue72));
    float2 floatValue74 =
        (float2((-quotientValue73.x), (-quotientValue73.y)) + float2(quotientValue71.x, quotientValue71.y));
    controlWords0.xyzw =
        uint4(asuint(floatValue74.x), asuint(floatValue74.y), asuint(quotientValue73.x), asuint(quotientValue73.y));
    controlWords1.xyzw = uint4(wordValue68, comparisonMask67, asuint(floatValue64), asuint(floatValue55.w));
    controlWords2.xyzw =
        uint4(asuint(floatValue52.x), asuint(floatValue52.y), asuint(floatValue52.z), asuint(floatValue52.w));
    controlWords3.xyz = uint3(asuint(floatValue35), wordValue34, wordValue33);

    float floatValue76 = (-asfloat(controlWords0.y));
    uint2 comparisonMask77 = uint2((asfloat(0x00000000u) < asfloat(controlWords0.x) ? 0xffffffffu : 0u),
                                   (asfloat(0x00000000u) < floatValue76 ? 0xffffffffu : 0u));
    uint2 comparisonMask78 = uint2((asfloat(controlWords0.x) < asfloat(0x00000000u) ? 0xffffffffu : 0u),
                                   (floatValue76 < asfloat(0x00000000u) ? 0xffffffffu : 0u));
    float2 floatValue79 = (float2(asfloat(controlWords0.x), asfloat(controlWords0.y)) *
                           float2(asfloat(0x3f000000u), asfloat(0xbf000000u)));
    float2 squareRoot80 = sqrt(float2(abs(floatValue79.x), abs(floatValue79.y)));
    float2 squareRoot81 = sqrt(float2(squareRoot80.x, squareRoot80.y));
    uint2 wordValue82 = (int2((-asint(comparisonMask77.x)), (-asint(comparisonMask77.y))) +
                         uint2(comparisonMask78.x, comparisonMask78.y));
    float2 floatValue83 = (float2)(int2(asint(wordValue82.x), asint(wordValue82.y)));
    float2 floatValue84 = (float2(floatValue83.x, floatValue83.y) * float2(squareRoot81.x, squareRoot81.y));
    float2 floatValue85 =
        mad(float2(floatValue84.x, floatValue84.y), float2(asfloat(0x3f000000u), asfloat(0x3f000000u)),
            float2(asfloat(0x3f000000u), asfloat(0x3f000000u)));
    float floatValue86 = (asfloat(0x3f800000u) + _ParticleHighlightResponse.y);
    float floatValue87 = saturate((floatValue86 + (-_ParticleHighlightResponse.x)));
    float2 floatValue88 = (float2(floatValue87, floatValue87) * float2(floatValue85.x, floatValue85.y));
    o1.xy = asuint(min(float2(floatValue88.x, floatValue88.y), float2(asfloat(0x3f800000u), asfloat(0x3f800000u))));
    // mov o1.zw, l(0x00000000,0x00000000,0x3f800000,0x00000000)
    o1.zw = uint2(0x3f800000u, 0x00000000u);
    // 输出边界只恢复源通道的浮点视图；位载体在这里按原SV_Target/SV_Depth接口写出。
    _output0 = asfloat(o0.xyzw);
    _output1 = asfloat(o1.xyzw);
    controlWords0.xyzw =
        uint4(asuint(floatValue88.x), asuint(floatValue88.y), asuint(floatValue87), asuint(floatValue83.y));
    controlWords1.xy = uint2(comparisonMask77.x, comparisonMask77.y);
    return;
}
