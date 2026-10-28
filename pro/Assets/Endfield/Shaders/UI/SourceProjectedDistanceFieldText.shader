// 源UI片元实际指令；CB页已映射为用途参数。几何仅保存静态capture的真实VS插值。
Shader "Endfield/UI/SourceProjectedDistanceFieldText" {Properties {
_WaveTimeControl("WaveTimeControl",Vector)=(0,0,0,0)
_WaveEnabled("WaveEnabled",Vector)=(0,0,0,0)
_DirectionalFade("DirectionalFade",Vector)=(0,0,0,0)
_WaveParameters("WaveParameters",Vector)=(0,0,0,0)
_GlyphSamplingAndSoftness("GlyphSamplingAndSoftness",Vector)=(0,0,0,0)
_OpacityControl("OpacityControl",Vector)=(0,0,0,0)
_FaceUVScroll("FaceUVScroll",Vector)=(0,0,0,0)
_FaceColor("FaceColor",Color)=(0,0,0,0)
_OutlineSoftnessAndUVScroll("OutlineSoftnessAndUVScroll",Vector)=(0,0,0,0)
_OutlineColor("OutlineColor",Color)=(0,0,0,0)
_OutlineWidth("OutlineWidth",Vector)=(0,0,0,0)
_DistanceFieldScale("DistanceFieldScale",Vector)=(0,0,0,0)
_FontAtlasDimensions("FontAtlasDimensions",Vector)=(0,0,0,0)
_GlyphPadding("GlyphPadding",Vector)=(0,0,0,0)
_AnimationPhase("AnimationPhase",Vector)=(0,0,0,0)
_ReferenceViewport("ReferenceViewport",Vector)=(0,0,0,0)
[HideInInspector] _UITexture0("UI Atlas 0",2D)="white"{}
[HideInInspector] _UITexture1("UI Atlas 1",2D)="white"{}
[HideInInspector] _UITexture2("UI Atlas 2",2D)="white"{}
[HideInInspector] _UITexture3("UI Atlas 3",2D)="white"{}
[HideInInspector] _UITexture4("UI Atlas 4",2D)="white"{}
[HideInInspector] _srcBlend("srcBlend",Float)=1
[HideInInspector] _dstBlend("dstBlend",Float)=10
[HideInInspector] _srcBlendAlpha("srcBlendAlpha",Float)=1
[HideInInspector] _dstBlendAlpha("dstBlendAlpha",Float)=10
[HideInInspector] _blendOp("blendOp",Float)=0
[HideInInspector] _blendOpAlpha("blendOpAlpha",Float)=0
[HideInInspector] _colorMask("colorMask",Float)=15
[HideInInspector] _cull("cull",Float)=0
[HideInInspector] _zTest("zTest",Float)=8
[HideInInspector] _zWrite("zWrite",Float)=0
[HideInInspector] _stencilRef("stencilRef",Float)=0
[HideInInspector] _stencilReadMask("stencilReadMask",Float)=255
[HideInInspector] _stencilWriteMask("stencilWriteMask",Float)=0
[HideInInspector] _stencilCompFront("stencilCompFront",Float)=8
[HideInInspector] _stencilCompBack("stencilCompBack",Float)=8
[HideInInspector] _stencilPassFront("stencilPassFront",Float)=0
[HideInInspector] _stencilPassBack("stencilPassBack",Float)=0
[HideInInspector] _stencilFailFront("stencilFailFront",Float)=0
[HideInInspector] _stencilFailBack("stencilFailBack",Float)=0
[HideInInspector] _stencilZFailFront("stencilZFailFront",Float)=0
[HideInInspector] _stencilZFailBack("stencilZFailBack",Float)=0
} SubShader {Tags {"RenderPipeline"="EndfieldPipeline"} Pass {
Cull [_cull]
ZWrite [_zWrite] ZTest [_zTest]
Blend [_srcBlend] [_dstBlend], [_srcBlendAlpha] [_dstBlendAlpha]
BlendOp [_blendOp], [_blendOpAlpha] ColorMask [_colorMask]
Stencil {Ref [_stencilRef] ReadMask [_stencilReadMask] WriteMask [_stencilWriteMask]
CompFront [_stencilCompFront] CompBack [_stencilCompBack] PassFront [_stencilPassFront] PassBack [_stencilPassBack]
FailFront [_stencilFailFront] FailBack [_stencilFailBack] ZFailFront [_stencilZFailFront] ZFailBack [_stencilZFailBack]}
HLSLPROGRAM
#pragma target 5.0
#pragma vertex UIVertex
#pragma fragment UIFragment
#pragma multi_compile_local __ UI_S0_CLAMP
#pragma multi_compile_local __ UI_S0_POINT
#pragma multi_compile_local __ UI_S1_CLAMP
#pragma multi_compile_local __ UI_S1_POINT
#pragma multi_compile_local __ UI_S2_CLAMP
#pragma multi_compile_local __ UI_S2_POINT
#include "Packages/com.unity.render-pipelines.core/ShaderLibrary/Common.hlsl"
CBUFFER_START(UnityPerMaterial)
float4 _WaveTimeControl; // y:源波动时间输入
float4 _WaveEnabled; // x:字形波动开关
float4 _DirectionalFade; // w:方向性透明渐变
float4 _WaveParameters; // xyzw:振幅、频率、相位速度、幂次
float4 _GlyphSamplingAndSoftness; // x多点采样/y面柔度/z采样半径/w边柔度
float4 _OpacityControl; // x:输出alpha减量
float4 _FaceUVScroll; // xy:面纹理UV相位系数
float4 _FaceColor; // RGBA:字形面色
float4 _OutlineSoftnessAndUVScroll; // y轮廓柔度/zw轮廓UV相位系数
float4 _OutlineColor; // RGBA:字形轮廓色
float4 _OutlineWidth; // x:轮廓宽度
float4 _DistanceFieldScale; // w:距离场梯度尺度
float4 _FontAtlasDimensions; // zw:字体图集宽高
float4 _GlyphPadding; // x:波动UV约束
float4 _AnimationPhase; // y:面/轮廓UV滚动相位
float4 _ReferenceViewport; // xy:波动宽高比参考尺寸
CBUFFER_END
SamplerState sampler_UI_linear_repeat;
SamplerState sampler_UI_linear_clamp;
SamplerState sampler_UI_point_repeat;
SamplerState sampler_UI_point_clamp;
#if defined(UI_S0_POINT)
 #if defined(UI_S0_CLAMP)
  #define _UISampler0 sampler_UI_point_clamp
 #else
  #define _UISampler0 sampler_UI_point_repeat
 #endif
#else
 #if defined(UI_S0_CLAMP)
  #define _UISampler0 sampler_UI_linear_clamp
 #else
  #define _UISampler0 sampler_UI_linear_repeat
 #endif
#endif
#if defined(UI_S1_POINT)
 #if defined(UI_S1_CLAMP)
  #define _UISampler1 sampler_UI_point_clamp
 #else
  #define _UISampler1 sampler_UI_point_repeat
 #endif
#else
 #if defined(UI_S1_CLAMP)
  #define _UISampler1 sampler_UI_linear_clamp
 #else
  #define _UISampler1 sampler_UI_linear_repeat
 #endif
#endif
#if defined(UI_S2_POINT)
 #if defined(UI_S2_CLAMP)
  #define _UISampler2 sampler_UI_point_clamp
 #else
  #define _UISampler2 sampler_UI_point_repeat
 #endif
#else
 #if defined(UI_S2_CLAMP)
  #define _UISampler2 sampler_UI_linear_clamp
 #else
  #define _UISampler2 sampler_UI_linear_repeat
 #endif
#endif
Texture2D<float4> _UITexture2;

Texture2D<float4> _UITexture1;

Texture2D<float4> _UITexture0;


















// 3Dmigoto declarations
#define cmp -


void SourceUI(float4 v0,float4 v1,float4 v2,float4 v3,float4 v4,float4 v5,float4 v6,float4 v7,float4 v8,float4 v9,out float4 o0) {
  float4 r0,r1,r2,r3,r4;
  uint4 bitmask, uiDest;
  float4 fDest;

  r0.x = cmp(0.5 < _WaveEnabled.x);
  r1.z = _WaveParameters.z * _WaveTimeControl.y;
  r0.y = max(9.99999975e-05, v9.w);
  r2.yz = v9.xy / r0.yy;
  r0.y = max(_ReferenceViewport.y, 1);
  r0.y = _ReferenceViewport.x / r0.y;
  r2.x = r2.y * r0.y;
  r0.yz = _WaveParameters.yy * r2.xz;
  r1.xyw = float3(-0.970000029,1.30999994,0.829999983) * r1.zzz;
  r1.zw = r2.xz * _WaveParameters.yy + r1.zw;
  r0.yz = r0.yz * float2(1.70000005,1.70000005) + r1.xy;
  r0.w = sin(r1.w);
  r0.z = sin(r0.z);
  r1.x = r0.z * 0.5 + r0.w;
  r0.z = cos(r1.z);
  r0.y = cos(r0.y);
  r1.y = r0.y * 0.5 + r0.z;
  r0.yz = float2(0.666700006,0.666700006) * r1.xy;
  r0.w = _GlyphPadding.x + -1;
  r0.w = max(0, r0.w);
  r1.zw = cmp(float2(0,0) < r1.xy);
  r1.xy = cmp(r1.xy < float2(0,0));
  r1.xy = (int2)-r1.zw + (int2)r1.xy;
  r1.xy = (int2)r1.xy;
  r1.z = max(_WaveParameters.w, 1);
  r0.yz = log2(abs(r0.yz));
  r0.yz = r1.zz * r0.yz;
  r0.yz = exp2(r0.yz);
  r0.yz = r1.xy * r0.yz;
  r0.yz = _WaveParameters.xx * r0.yz;
  r0.yz = max(r0.yz, -r0.ww);
  r0.yz = min(r0.yz, r0.ww);
  r1.xy = float2(1,1) / _FontAtlasDimensions.zw;
  r0.yz = r1.xy * r0.yz;
  r0.yz = r0.xx ? r0.yz : 0;
  r0.yz = v2.xy + r0.yz;
  r0.w = _UITexture2.Sample(_UISampler2, r0.yz).x;
  r1.z = cmp(0.5 < _GlyphSamplingAndSoftness.x);
  if (r1.z != 0) {
    r2.xy = _GlyphSamplingAndSoftness.zz * r1.xy;
    r2.z = 0;
    r3.xyzw = r2.xzzy + r0.yzyz;
    r1.x = _UITexture2.Sample(_UISampler2, r3.xy).x;
    r1.x = r1.x + r0.w;
    r2.w = -r2.x;
    r1.yw = r2.wz + r0.yz;
    r1.y = _UITexture2.Sample(_UISampler2, r1.yw).x;
    r1.x = r1.x + r1.y;
    r1.y = _UITexture2.Sample(_UISampler2, r3.zw).x;
    r1.x = r1.x + r1.y;
    r0.yz = r2.zy * float2(1,-1) + r0.yz;
    r0.y = _UITexture2.Sample(_UISampler2, r0.yz).x;
    r0.y = r1.x + r0.y;
    r0.w = 0.200000003 * r0.y;
  }
  r0.y = v3.z + -r0.w;
  r0.z = _DistanceFieldScale.w * _OutlineWidth.x;
  r0.z = v3.y * r0.z;
  r0.w = _DistanceFieldScale.w * _OutlineSoftnessAndUVScroll.y;
  r1.x = v3.y * r0.w;
  r2.xyz = _FaceColor.xyz * v1.xyz;
  r1.yw = _FaceUVScroll.xy * _AnimationPhase.yy + v8.xy;
  r3.xyzw = _UITexture1.Sample(_UISampler1, r1.yw).xyzw;
  r2.xyz = r3.xyz * r2.xyz;
  r3.w = _FaceColor.w * r3.w;
  r1.yw = _OutlineSoftnessAndUVScroll.zw * _AnimationPhase.yy + v8.zw;
  r4.xyzw = _UITexture0.Sample(_UISampler0, r1.yw).xyzw;
  r4.xyzw = _OutlineColor.xyzw * r4.xyzw;
  r1.yw = _DistanceFieldScale.ww * _GlyphSamplingAndSoftness.yw;
  r3.xyz = r3.www * r2.xyz;
  r2.xy = v3.yy * r1.yw;
  r1.y = 0.5 * r2.x;
  r1.y = r0.y * v3.y + -r1.y;
  r1.y = r2.y * 0.5 + r1.y;
  r1.w = r1.w * v3.y + 1;
  r1.y = saturate(r1.y / r1.w);
  r1.y = 1 + -r1.y;
  r2.xyzw = r3.xyzw * r1.yyyy;
  r1.y = 0.5 * r0.z;
  r4.xyz = r4.xyz * r4.www;
  r1.w = saturate(r0.y * v3.y + r1.y);
  r0.z = min(1, r0.z);
  r0.z = sqrt(r0.z);
  r0.z = r1.w * r0.z;
  r4.xyzw = r4.xyzw + -r3.xyzw;
  r3.xyzw = r0.zzzz * r4.xyzw + r3.xyzw;
  r0.y = r0.y * v3.y + -r1.y;
  r0.y = r1.x * 0.5 + r0.y;
  r0.z = r0.w * v3.y + 1;
  r0.y = saturate(r0.y / r0.z);
  r0.y = 1 + -r0.y;
  r3.xyzw = r3.xyzw * r0.yyyy;
  r1.xyzw = r1.zzzz ? r2.xyzw : r3.xyzw;
  r0.y = _UITexture2.Sample(_UISampler2, v6.xy).x;
  r0.y = saturate(r0.y * v6.z + -v6.w);
  r2.xyzw = v7.xyzw * r0.yyyy;
  r0.y = 1 + -r1.w;
  r1.xyzw = r2.xyzw * r0.yyyy + r1.xyzw;
  r0.y = cmp(_DirectionalFade.w >= 0);
  r0.z = 1 + -v5.w;
  r0.y = r0.y ? r0.z : v5.w;
  r0.y = -1 + r0.y;
  r0.y = saturate(abs(_DirectionalFade.w) * r0.y + 1);
  r2.xyzw = r1.xyzw * r0.yyyy;
  r0.xyzw = r0.xxxx ? r2.xyzw : r1.xyzw;
  r0.xyzw = v1.wwww * r0.xyzw;
  o0.w = _OpacityControl.x * -r0.w + r0.w;
  o0.xyz = r0.xyz;
  return;
}
float4 _EndfieldOutputScaleBias;
struct UIInput { float4 clip:POSITION;float4 o1:COLOR;float4 o2:TEXCOORD0;float4 o3:TEXCOORD1;float4 o4:TEXCOORD2;float4 o5:TEXCOORD3;float4 o6:TEXCOORD4;float4 o7:TEXCOORD5;float4 o8:TEXCOORD6;float4 o9:TEXCOORD7;};
struct UIVaryings {float4 position:SV_POSITION;float4 o1:TEXCOORD0;float4 o2:TEXCOORD1;float4 o3:TEXCOORD2;float4 o4:TEXCOORD3;float4 o5:TEXCOORD4;float4 o6:TEXCOORD5;float4 o7:TEXCOORD6;float4 o8:TEXCOORD7;float4 o9:TEXCOORD8;};
UIVaryings UIVertex(UIInput i){UIVaryings o;o.position=float4(i.clip.x,-i.clip.y*_EndfieldOutputScaleBias.y,i.clip.zw);o.o1=i.o1;o.o2=i.o2;o.o3=i.o3;o.o4=i.o4;o.o5=i.o5;o.o6=i.o6;o.o7=i.o7;o.o8=i.o8;o.o9=i.o9;return o;}
float4 UIFragment(UIVaryings i):SV_Target{float4 color=0;SourceUI(i.position,i.o1,i.o2,i.o3,i.o4,i.o5,i.o6,i.o7,i.o8,i.o9,color);return color;}
ENDHLSL
}}}
