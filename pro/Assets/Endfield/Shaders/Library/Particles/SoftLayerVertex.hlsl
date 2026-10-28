// 几何/插值适配 animated_uv：把网格属性与公共顶点结果整理成所选片元公式的参数布局。
// 整数插值保持不插值：instanceIndex:TEXCOORD5；不能改成浮点插值。

// Geometry/varying ABI: animated_uv.
// This wrapper preserves its interpolator widths and integer/nointerpolation fields.
// EFParticleBuildUnityBasis owns object/current/previous deformation and clip transforms.
// baseUv <- uvData
// additionalUv <- input.extra1
// vertexColor <- vertexColor
// currentClipXYW <- float4(b.currentClip.xyw,0)
// previousClipXYW <- float4(b.previousClip.xyw,0)
// instanceIndex <- 0u
struct EFParticleVaryings
{
    float4 position : SV_POSITION;
    float4 baseUv : TEXCOORD0;
    float4 additionalUv : TEXCOORD1;
    float4 vertexColor : TEXCOORD2;
    float4 currentClipXYW : TEXCOORD3;
    float4 previousClipXYW : TEXCOORD4;
    nointerpolation uint instanceIndex : TEXCOORD5;


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
    float3 viewOffset = viewRay / viewDistance * (.001 + min(_ParticleVertexViewControl.y, max(0, viewDistance - 1)));
    viewOffset *= 1.0 - asfloat(asuint(float4(unity_OrthoParams.w,0,0,0))).x;
    b.world += viewOffset;
    b.currentClip = mul(unity_MatrixVP, float4(b.world, 1));
    b.position = b.currentClip;
    b.position.xy -= float4(0,0,0,0).xy * b.currentClip.w;
    b.previousClip += mul(_EndfieldPreviousViewProjection, float4(viewOffset, 0));
    float4 vertexColor = _ParticleVertexViewControl.z != 0 ? input.color : input.color * (1.0 - _ParticleVertexFade);
    float4 uvPair = input.extra1.xxyy + (input.extra0.zzww - input.extra1.xxyy) * _ParticleVertexStreamControl.x;
    uvPair = uvPair * _PrimaryUvWeights.y + input.extra0.xxyy * _PrimaryUvWeights.x;
    uvPair += _PrimaryUvVelocity.xxyy * (asfloat(asuint(float4(0,0,0,_ParticlePhase+_Time.y*_ParticlePhaseSpeed))).w + 0);
    uvPair += _PrimaryUvVelocity.zzww * (input.extra1.x * _ParticleVertexStreamControl.x);
    uvPair = (uvPair - .5) * _PrimaryUvRotation;
    float4 uvData = float4((uvPair.xy + uvPair.zw + .5) * _PrimaryUvTransform.xy + _PrimaryUvTransform.zw,
                           input.extra1.zw * _ParticleVertexStreamControl.x);

    output.position = b.position;
    output.baseUv = uvData;
    output.additionalUv = input.extra1;
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
    EFParticleEvaluateSoftLayer(input.position, input.baseUv.xyzw, input.additionalUv.xyzw, input.vertexColor.xyzw,
                                input.currentClipXYW.xyz, input.previousClipXYW.xyz, input.instanceIndex, output.target0,
                                output.target1

    );
    return output.target0;
}
