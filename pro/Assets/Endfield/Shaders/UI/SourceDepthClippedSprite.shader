// 源UI片元实际指令；CB页已映射为用途参数。几何仅保存静态capture的真实VS插值。
Shader "Endfield/UI/SourceDepthClippedSprite" {Properties {
_DepthLinearization("DepthLinearization",Vector)=(0,0,0,0)
_TextureSampleAdd("TextureSampleAdd",Vector)=(0,0,0,0)
_OpacityControl("OpacityControl",Vector)=(0,0,0,0)
_TextureAlphaAndDepthControl("TextureAlphaAndDepthControl",Vector)=(0,0,0,0)
_DepthClipOffset("DepthClipOffset",Vector)=(0,0,0,0)
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
float4 _DepthLinearization; // zw:源倒数深度系数
float4 _TextureSampleAdd; // RGBA:采样相加项
float4 _OpacityControl; // x:输出alpha减量
float4 _TextureAlphaAndDepthControl; // x忽略纹理alpha/y深度插值/z参考深度或灰度混合/w深度偏移
float4 _DepthClipOffset; // x:深度裁剪偏移尺度
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
Texture2D<float4> _CameraDepthTexture;

Texture2D<float4> _UITexture0;














// 3Dmigoto declarations
#define cmp -


void SourceUI(float4 v0,float4 v1,float4 v2,float4 v3,float4 v4,float4 v5,float4 v6,out float4 o0) {
  float4 r0,r1,r2;
  uint4 bitmask, uiDest;
  float4 fDest;

  r0.xyz = v6.zxy / v6.www;
  r0.w = _TextureAlphaAndDepthControl.z + -r0.x;
  r0.x = _TextureAlphaAndDepthControl.y * r0.w + r0.x;
  r0.y = _CameraDepthTexture.Sample(_UISampler1, r0.yz).x;
  r0.y = _DepthLinearization.z * r0.y + _DepthLinearization.w;
  r0.y = 1 / r0.y;
  r0.x = saturate(_TextureAlphaAndDepthControl.w * -_DepthClipOffset.x + r0.x);
  r0.x = _DepthLinearization.z * r0.x + _DepthLinearization.w;
  r0.x = 1 / r0.x;
  r0.x = r0.y + -r0.x;
  r0.x = cmp(r0.x < 0);
  if (r0.x != 0) discard;
  r0.x = 255 * v1.w;
  r0.x = round(r0.x);
  r0.w = 0.00392156886 * r0.x;
  r1.xyzw = _UITexture0.Sample(_UISampler0, v2.xy).xyzw;
  r2.x = cmp(0.000000 != _TextureAlphaAndDepthControl.x);
  r1.w = r2.x ? 1 : r1.w;
  r1.xyzw = _TextureSampleAdd.xyzw + r1.xyzw;
  r0.xyz = v1.xyz;
  r0.xyzw = r1.xyzw * r0.xyzw;
  o0.xyz = r0.xyz * r0.www;
  o0.w = _OpacityControl.x * -r0.w + r0.w;
  return;
}
float4 _EndfieldOutputScaleBias;
struct UIInput { float4 clip:POSITION;float4 o1:COLOR;float4 o2:TEXCOORD0;float4 o3:TEXCOORD1;float4 o4:TEXCOORD2;float4 o5:TEXCOORD3;float4 o6:TEXCOORD4;float4 o7:TEXCOORD5;float4 o8:TEXCOORD6;float4 o9:TEXCOORD7;};
struct UIVaryings {float4 position:SV_POSITION;float4 o1:TEXCOORD0;float4 o2:TEXCOORD1;float4 o3:TEXCOORD2;float4 o4:TEXCOORD3;float4 o5:TEXCOORD4;float4 o6:TEXCOORD5;float4 o7:TEXCOORD6;float4 o8:TEXCOORD7;float4 o9:TEXCOORD8;};
UIVaryings UIVertex(UIInput i){UIVaryings o;o.position=float4(i.clip.x,-i.clip.y*_EndfieldOutputScaleBias.y,i.clip.zw);o.o1=i.o1;o.o2=i.o2;o.o3=i.o3;o.o4=i.o4;o.o5=i.o5;o.o6=i.o6;o.o7=i.o7;o.o8=i.o8;o.o9=i.o9;return o;}
float4 UIFragment(UIVaryings i):SV_Target{float4 color=0;SourceUI(i.position,i.o1,i.o2,i.o3,i.o4,i.o5,i.o6,color);return color;}
ENDHLSL
}}}
