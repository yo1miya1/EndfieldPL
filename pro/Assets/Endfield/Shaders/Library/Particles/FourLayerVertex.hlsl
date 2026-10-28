// 几何/插值适配 animated_uv4：把网格属性与公共顶点结果整理成所选片元公式的参数布局。
// 整数插值保持不插值：instanceIndex:TEXCOORD6；不能改成浮点插值。

// Geometry/varying ABI: animated_uv4.
// This wrapper preserves its interpolator widths and integer/nointerpolation fields.
// EFParticleBuildUnityBasis owns object/current/previous deformation and clip transforms.
// baseUv <- uvData0
// maskNoiseUv <- uvData1
// overlayUv <- uvData2
// vertexColor <- vertexColor
// currentClipXYW <- float4(b.currentClip.xyw,0)
// previousClipXYW <- float4(b.previousClip.xyw,0)
// instanceIndex <- 0u
struct EFParticleVaryings
{
    float4 position : SV_POSITION;
    float4 baseUv : TEXCOORD0;
    float4 maskNoiseUv : TEXCOORD1;
    float4 overlayUv : TEXCOORD2;
    float4 vertexColor : TEXCOORD3;
    float4 currentClipXYW : TEXCOORD4;
    float4 previousClipXYW : TEXCOORD5;
    nointerpolation uint instanceIndex : TEXCOORD6;


};
struct EFParticleLeafOutputs
{
    float4 target0 : SV_Target0;
    float4 target1 : SV_Target1;
};
// 建立此变体的插值数据；semantic编号和向量宽度必须与片元公式逐项对应。
EFParticleVaryings EFParticleVertex(EFParticleAttributes input)
{
    EFParticleVaryings output;
    EFParticleUnityBasis b = EFParticleBuildUnityBasis(input);
    float3 viewRay = _WorldSpaceCameraPos.xyz - b.world;
    float viewDistance = length(viewRay);
    float3 viewOffset = viewRay / max(viewDistance, 1e-30) *
                        (.001 + min(_ParticleVertexViewControl.y, max(0, viewDistance - 1))) * (1 - asfloat(asuint(float4(unity_OrthoParams.w,0,0,0))).x);
    b.world += viewOffset;
    b.currentClip = mul(unity_MatrixVP, float4(b.world, 1));
    b.position = b.currentClip;
    b.position.xy -= float4(0,0,0,0).xy * b.currentClip.w;
    b.previousClip += mul(_EndfieldPreviousViewProjection, float4(viewOffset, 0));
    float4 vertexColor = _ParticleVertexViewControl.z != 0 ? input.color : input.color * (1 - _ParticleVertexFade);
    float4 uvPair = input.extra1.xxyy + (input.extra0.zzww - input.extra1.xxyy) * _ParticleVertexStreamControl.x;
    float4 uvFactor = input.extra1 * _ParticleVertexStreamControl.x;
    float sourceTime = asfloat(asuint(float4(0,0,0,_ParticlePhase+_Time.y*_ParticlePhaseSpeed))).w + 0;
    float4 uvWork0 = input.extra0.xxyy * _PrimaryUvWeights.x + uvPair.yyww * _PrimaryUvWeights.y;
    uvWork0 += _PrimaryUvVelocity.xxyy * sourceTime + _PrimaryUvVelocity.zzww * uvFactor.x;
    uvWork0 = (uvWork0 - .5) * _PrimaryUvRotation;
    float2 uvSum0 = uvWork0.xy + uvWork0.zw + .5;
    float4 uvData0 = float4(uvSum0 * _PrimaryUvTransform.xy + _PrimaryUvTransform.zw, uvFactor.zw);
    float4 uvMatrix1 = _UvSharedTransformC * _MaskUvLayerWeights.x + _UvExtraTransformB * _MaskUvLayerWeights.y +
                       _UvExtraTransformC * _MaskUvLayerWeights.z;
    float4 uvWork1 = input.extra0.xxyy * _MaskUvWeights.x + uvPair.yyww * _MaskUvWeights.y;
    uvWork1 += _MaskUvVelocity.xxyy * sourceTime + _MaskUvVelocity.zzww * uvFactor.y;
    uvWork1 = (uvWork1 - .5) * _MaskUvRotation;
    float2 uvSum1 = uvWork1.xy + uvWork1.zw + .5;
    float4 uvMatrix2 = _UvExtraTransformA * _NoiseUvLayerWeights.x + _UvExtraTransformB * _NoiseUvLayerWeights.y +
                       _UvExtraTransformC * _NoiseUvLayerWeights.z + _UvExtraTransformD * _NoiseUvLayerWeights.w;
    float4 uvWork2 = input.extra0.xxyy * _NoiseUvWeights.x + uvPair.yyww * _NoiseUvWeights.y;
    uvWork2 += _NoiseUvVelocity.xxyy * sourceTime + _NoiseUvVelocity.zzww * uvFactor.y;
    uvWork2 = (uvWork2 - .5) * _NoiseUvRotation;
    float2 uvSum2 = uvWork2.xy + uvWork2.zw + .5;
    float4 uvData1 = float4(uvSum1 * uvMatrix1.xy + uvMatrix1.zw, uvSum2 * uvMatrix2.xy + uvMatrix2.zw);
    float4 uvMatrix3 = _UvExtraTransformB * _OverlayUvLayerWeights.x + _UvExtraTransformC * _OverlayUvLayerWeights.y +
                       _UvExtraTransformD * _OverlayUvLayerWeights.z + _UvExtraTransformE * _OverlayUvLayerWeights.w;
    float4 uvWork3 = input.extra0.xxyy * _OverlayUvWeights.x + uvPair.yyww * _OverlayUvWeights.y;
    uvWork3 += _OverlayUvVelocity.xxyy * sourceTime + _OverlayUvVelocity.zzww * uvFactor.y;
    uvWork3 = (uvWork3 - .5) * _OverlayUvRotation;
    float2 uvSum3 = uvWork3.xy + uvWork3.zw + .5;
    float4 uvData2 = float4(uvSum3 * uvMatrix3.xy + uvMatrix3.zw, 0, 0);

    output.position = b.position;
    output.baseUv = uvData0;
    output.maskNoiseUv = uvData1;
    output.overlayUv = uvData2;
    output.vertexColor = vertexColor;
    output.currentClipXYW = float4(b.currentClip.xyw, 0);
    output.previousClipXYW = float4(b.previousClip.xyw, 0);
    output.instanceIndex = 0u;

    return output;
}
// 只适配插值参数并接收原公式输出；未写的目标不能额外补零写入。
float4 EFParticleFragment(EFParticleVaryings input, bool frontFace : SV_IsFrontFace) : SV_Target
{
    EFParticleLeafOutputs output;
    EFParticleEvaluateFourLayer(input.position, input.baseUv.xyzw, input.maskNoiseUv.xyzw, input.overlayUv.xyzw,
                                input.vertexColor.xyzw, input.currentClipXYW.xyz, input.previousClipXYW.xyz, input.instanceIndex,
                                output.target0, output.target1

    );
    return output.target0;
}
