// 源UI片元实际指令；CB页已映射为用途参数。几何仅保存静态capture的真实VS插值。
Shader "Endfield/UI/SourceSceneMaskedSprite" {Properties {
_TextureSampleAdd("TextureSampleAdd",Vector)=(0,0,0,0)
_SceneBrightness("SceneBrightness",Vector)=(0,0,0,0)
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
#include "Packages/com.unity.render-pipelines.core/ShaderLibrary/Common.hlsl"
CBUFFER_START(UnityPerMaterial)
float4 _TextureSampleAdd; // RGBA:采样相加项
float4 _SceneBrightness; // x:源模糊场景颜色增益
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
Texture2D<float4> _UITexture1;

Texture2D<float4> _EndfieldUIBlurredSceneTexture;












// 3Dmigoto declarations
#define cmp -


void SourceUI(float4 v0,float4 v1,float4 v2,float4 v3,float4 v4,out float4 o0) {
  float4 r0;
  uint4 bitmask, uiDest;
  float4 fDest;

  r0.xyz = _EndfieldUIBlurredSceneTexture.SampleLevel(_UISampler0, v4.xy, 0).xyz;
  r0.xyz = v1.xyz * r0.xyz;
  o0.xyz = _SceneBrightness.xxx * r0.xyz;
  r0.x = _UITexture1.Sample(_UISampler1, v2.xy).w;
  r0.x = _TextureSampleAdd.w + r0.x;
  o0.w = v1.w * r0.x;
  return;
}
float4 _EndfieldOutputScaleBias;
struct UIInput { float4 clip:POSITION;float4 o1:COLOR;float4 o2:TEXCOORD0;float4 o3:TEXCOORD1;float4 o4:TEXCOORD2;float4 o5:TEXCOORD3;float4 o6:TEXCOORD4;float4 o7:TEXCOORD5;float4 o8:TEXCOORD6;float4 o9:TEXCOORD7;};
struct UIVaryings {float4 position:SV_POSITION;float4 o1:TEXCOORD0;float4 o2:TEXCOORD1;float4 o3:TEXCOORD2;float4 o4:TEXCOORD3;float4 o5:TEXCOORD4;float4 o6:TEXCOORD5;float4 o7:TEXCOORD6;float4 o8:TEXCOORD7;float4 o9:TEXCOORD8;};
UIVaryings UIVertex(UIInput i){UIVaryings o;o.position=float4(i.clip.x,-i.clip.y*_EndfieldOutputScaleBias.y,i.clip.zw);o.o1=i.o1;o.o2=i.o2;o.o3=i.o3;o.o4=i.o4;o.o5=i.o5;o.o6=i.o6;o.o7=i.o7;o.o8=i.o8;o.o9=i.o9;return o;}
float4 UIFragment(UIVaryings i):SV_Target{float4 color=0;SourceUI(i.position,i.o1,i.o2,i.o3,i.o4,color);return color;}
ENDHLSL
}}}
