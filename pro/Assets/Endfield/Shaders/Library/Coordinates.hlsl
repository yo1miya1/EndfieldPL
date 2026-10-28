#ifndef ENDFIELD_COORDINATES_INCLUDED
#define ENDFIELD_COORDINATES_INCLUDED
#include "Packages/com.unity.render-pipelines.core/ShaderLibrary/Common.hlsl"

// 使用 Unity 当前 Renderer/Camera 的矩阵；没有捕获相机或离线法线替代。
CBUFFER_START(UnityPerDraw)
// Space block Feature
float4x4 unity_ObjectToWorld;
float4x4 unity_WorldToObject;
float4 unity_LODFade; // x is the fade value ranging within [0,1]. y is x quantized into 16 levels
real4 unity_WorldTransformParams; // w is usually 1.0, or -1.0 for odd-negative scale transforms

// Render Layer block feature
// Only the first channel (x) contains valid data and the float must be reinterpreted using asuint() to extract the original 32 bits values.
float4 unity_RenderingLayer;

// Light Indices block feature
// These are set internally by the engine upon request by RendererConfiguration.
float4 unity_PackedLightIndices;
half4 unity_LightData;

float4 unity_ProbesOcclusion;

// Reflection Probe 0 block feature
// HDR environment map decode instructions
real4 unity_SpecCube0_HDR;
real4 unity_SpecCube1_HDR;

float4 unity_SpecCube0_BoxMax;          // w contains the blend distance
float4 unity_SpecCube0_BoxMin;          // w contains the lerp value
float4 unity_SpecCube0_ProbePosition;   // w is set to 1 for box projection
float4 unity_SpecCube0_Rotation;
float4 unity_SpecCube1_BoxMax;          // w contains the blend distance
float4 unity_SpecCube1_BoxMin;          // w contains the sign of (SpecCube0.importance - SpecCube1.importance)
float4 unity_SpecCube1_ProbePosition;   // w is set to 1 for box projection
float4 unity_SpecCube1_Rotation;

// Lightmap block feature
float4 unity_LightmapST;
float4 unity_DynamicLightmapST;

// SH block feature
real4 unity_SHAr;
real4 unity_SHAg;
real4 unity_SHAb;
real4 unity_SHBr;
real4 unity_SHBg;
real4 unity_SHBb;
real4 unity_SHC;

// Renderer bounding box.
float4 unity_RendererBounds_Min;
float4 unity_RendererBounds_Max;

// Velocity
float4x4 unity_MatrixPreviousM;
float4x4 unity_MatrixPreviousMI;
//X : Use last frame positions (right now skinned meshes are the only objects that use this
//Y : Force No Motion
//Z : Z bias value
//W : Camera only
float4 unity_MotionVectorsParams;

// Sprite.
float4 unity_SpriteColor;
//X : FlipX
//Y : FlipY
//Z : Reserved for future use.
//W : Reserved for future use.
float4 unity_SpriteProps;
CBUFFER_END
float4x4 unity_MatrixVP;
float4x4 unity_MatrixV;
float4x4 glstate_matrix_projection;
float3 _WorldSpaceCameraPos;
float4 _ProjectionParams;
float4 _ScreenParams;
float4 _ZBufferParams;
float4x4 _EndfieldInverseViewProjection;
float4x4 _EndfieldPreviousViewProjection;
float4x4 _EndfieldNonJitteredViewProjection;
float4x4 _TemporalPreviousViewProjection;
float _EndfieldHistoryValid;
float EFSquare(float x) { return x * x; }
float EFPow5(float x) { float x2 = x * x; return x2 * x2 * x; }
// Unity LightProbe/ambientProbe 的标准SH9，RendererList开启LightProbe逐物体输入。
// 此处读取引擎内置数据，场景光照更新不需要重导材质。
float3 EFUnityAmbient(float3 n)
{
    float4 normal = float4(n, 1);
    float3 color = float3(dot(unity_SHAr, normal), dot(unity_SHAg, normal), dot(unity_SHAb, normal));
    float4 quadratic = n.xyzz * n.yzzx;
    color += float3(dot(unity_SHBr, quadratic), dot(unity_SHBg, quadratic), dot(unity_SHBb, quadratic));
    color += unity_SHC.rgb * (n.x * n.x - n.y * n.y);
    return max(color, 0);
}

float3 EFWorldPosition(float3 p) { return mul(unity_ObjectToWorld, float4(p, 1)).xyz; }
float3 EFWorldNormal(float3 n) { return normalize(mul(n, (float3x3)unity_WorldToObject)); }
float3 EFWorldTangent(float3 t) { return normalize(mul((float3x3)unity_ObjectToWorld, t)); }
float4 EFClipPosition(float3 p) { return mul(unity_MatrixVP, float4(p, 1)); }
float2 EFSignNotZero(float2 v) { return float2(v.x >= 0 ? 1 : -1, v.y >= 0 ? 1 : -1); }

// 原库 SourceOctahedralEncoding 的 Y-up 八面体折叠；不能误用常见 Z-up 编码。
float2 EFEncodeNormal(float3 n)
{
    n /= max(dot(abs(n), 1.0), 1e-8);
    float2 p = n.xz;
    if (n.y <= 0) p = (1 - abs(p.yx)) * EFSignNotZero(p);
    return p * 0.5 + 0.5;
}
float3 EFDecodeNormal(float2 uv)
{
    float2 p = uv * 2 - 1;
    float3 n = float3(p.x, 1 - abs(p.x) - abs(p.y), p.y);
    if (n.y < 0) n.xz = (1 - abs(n.zx)) * EFSignNotZero(n.xz);
    return normalize(n);
}

// 原运动纹理使用带符号四次根；静止为 0.5，解码的结果为当前减前帧 UV。
float2 EFEncodeMotion(float2 uvDelta)
{
    return 0.5 + 0.5 * sign(uvDelta) * sqrt(sqrt(abs(uvDelta)));
}
float2 EFDecodeMotion(float2 encoded)
{
    float2 v = encoded * 2 - 1;
    return sign(v) * pow(abs(v), 4);
}
float3 EFReconstructWorld(float2 uv, float depth)
{
    return ComputeWorldSpacePosition(uv, depth, _EndfieldInverseViewProjection);
}

struct EFFullscreenVaryings { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; };
EFFullscreenVaryings EFFullscreenVertex(uint vertexID : SV_VertexID)
{
    EFFullscreenVaryings o;
    o.positionCS = GetFullScreenTriangleVertexPosition(vertexID);
    o.uv = GetFullScreenTriangleTexCoord(vertexID);
    return o;
}
#endif
