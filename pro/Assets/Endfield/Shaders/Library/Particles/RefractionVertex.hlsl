// 几何/插值适配 color_uv_shift：把网格属性与公共顶点结果整理成所选片元公式的参数布局。
// 整数插值保持不插值：instanceIndex:TEXCOORD5；不能改成浮点插值。

// Geometry/varying ABI: color_uv_shift.
// This wrapper preserves its interpolator widths and integer/nointerpolation fields.
// EFParticleBuildUnityBasis owns object/current/previous deformation and clip transforms.
// baseUv <- float4(input.extra0.xy,0,0)
// maskNoiseUv <- float4(input.extra1.xy,0,0)
// vertexColor <- vertexColor
// currentClipXYW <- float4(b.currentClip.xyw,0)
// previousClipXYW <- float4(b.previousClip.xyw,0)
// instanceIndex <- 0u
struct EFParticleVaryings
{
    float4 position : SV_POSITION;
    float4 baseUv : TEXCOORD0;
    float4 maskNoiseUv : TEXCOORD1;
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
    float3 viewOffset = viewRay / max(viewDistance, 1e-30) * .001 * (1 - asfloat(asuint(float4(unity_OrthoParams.w,0,0,0))).x);
    b.world += viewOffset;
    b.currentClip = mul(unity_MatrixVP, float4(b.world, 1));
    b.position = b.currentClip;
    b.position.xy -= float4(0,0,0,0).xy * b.currentClip.w;
    b.previousClip += mul(_EndfieldPreviousViewProjection, float4(viewOffset, 0));
    float4 vertexColor = _ParticleVertexColorControl.z != 0 ? input.color : input.color * (1 - _ParticleVertexFade);

    output.position = b.position;
    output.baseUv = float4(input.extra0.xy, 0, 0);
    output.maskNoiseUv = float4(input.extra1.xy, 0, 0);
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
    EFParticleEvaluateRefraction(input.position, input.baseUv.xy, input.maskNoiseUv.xy, input.vertexColor.xyzw,
                                input.currentClipXYW.xyz, input.previousClipXYW.xyz, input.instanceIndex, output.target0,
                                output.target1

    );
    return output.target0;
}
