// 本UI家族保持源片元算法，捕获页已拆为可编辑的用途参数。
// 几何携带真实源VS输出，材质不再绑定捕获CB数组或EID。
Shader "Endfield/UI/ScreenLayeredSprite" { Properties {
_TextureSampleAdd("TextureSampleAdd",Vector)=(0,0,0,0)
_TextureAlphaOverride("TextureAlphaOverride",Vector)=(0,0,0,0)
_PatternUVTransform("PatternUVTransform",Vector)=(0,0,0,0)
_PatternControl("PatternControl",Vector)=(0,0,0,0)
_GridColor("GridColor",Color)=(0,0,0,0)
_GridControl("GridControl",Vector)=(0,0,0,0)
_LayerFeatures("LayerFeatures",Vector)=(0,0,0,0)
_LayerScreenAndDepth("LayerScreenAndDepth",Vector)=(0,0,0,0)
_DitherResolution("Dither Resolution",Vector)=(2560,1440,0,0)
_AlphaReduction("Alpha Reduction", Range(0,1))=0
[HideInInspector] _UITexture0("Source Texture 0",2D)="white"{}
[HideInInspector] _UITexture1("Source Texture 1",2D)="white"{}
[HideInInspector] _UITexture2("Source Texture 2",2D)="white"{}
[HideInInspector] _UITexture3("Source Texture 3",2D)="white"{}
[HideInInspector] _UITexture4("Source Texture 4",2D)="white"{}
[HideInInspector] _srcBlend("srcBlend",Float)=1
[HideInInspector] _dstBlend("dstBlend",Float)=10
[HideInInspector] _srcBlendAlpha("srcBlendAlpha",Float)=1
[HideInInspector] _dstBlendAlpha("dstBlendAlpha",Float)=10
[HideInInspector] _blendOp("blendOp",Float)=0
[HideInInspector] _blendOpAlpha("blendOpAlpha",Float)=0
[HideInInspector] _colorMask("colorMask",Float)=15
[HideInInspector] _zTest("zTest",Float)=8
[HideInInspector] _zWrite("zWrite",Float)=0
[HideInInspector] _stencilRef("stencilRef",Float)=0
[HideInInspector] _stencilReadMask("stencilReadMask",Float)=255
[HideInInspector] _stencilWriteMask("stencilWriteMask",Float)=255
[HideInInspector] _stencilCompFront("stencilCompFront",Float)=8
[HideInInspector] _stencilPassFront("stencilPassFront",Float)=0
[HideInInspector] _stencilFailFront("stencilFailFront",Float)=0
[HideInInspector] _stencilZFailFront("stencilZFailFront",Float)=0
[HideInInspector] _stencilCompBack("stencilCompBack",Float)=8
[HideInInspector] _stencilPassBack("stencilPassBack",Float)=0
[HideInInspector] _stencilFailBack("stencilFailBack",Float)=0
[HideInInspector] _stencilZFailBack("stencilZFailBack",Float)=0
} SubShader { Tags { "RenderPipeline"="EndfieldPipeline" } Pass { Cull Off
ZWrite [_zWrite]
ZTest [_zTest]
Blend [_srcBlend] [_dstBlend], [_srcBlendAlpha] [_dstBlendAlpha]
BlendOp [_blendOp], [_blendOpAlpha]
ColorMask [_colorMask]
Stencil { Ref [_stencilRef] ReadMask [_stencilReadMask] WriteMask [_stencilWriteMask] CompFront [_stencilCompFront] CompBack [_stencilCompBack] PassFront [_stencilPassFront] PassBack [_stencilPassBack] FailFront [_stencilFailFront] FailBack [_stencilFailBack] ZFailFront [_stencilZFailFront] ZFailBack [_stencilZFailBack] }
HLSLPROGRAM
#pragma target 5.0
#pragma vertex UIVertex
#pragma fragment UIFragment

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
#if defined(UI_S3_POINT)
 #if defined(UI_S3_CLAMP)
  #define _UISampler3 sampler_UI_point_clamp
 #else
  #define _UISampler3 sampler_UI_point_repeat
 #endif
#else
 #if defined(UI_S3_CLAMP)
  #define _UISampler3 sampler_UI_linear_clamp
 #else
  #define _UISampler3 sampler_UI_linear_repeat
 #endif
#endif

float4 _EndfieldOutputScaleBias; // 相机输出RT与backbuffer的Y适配，与世界坐标无关
float _AlphaReduction;
float4 _TextureSampleAdd; // 采样RGBA相加项
float4 _TextureAlphaOverride; // x非零时忽略图集alpha
float4 _PatternUVTransform; // xy缩放zw偏移，进入源固定200倍纹样坐标
float4 _PatternControl; // x纹样反差，y乘法亮度，z启用
float4 _GridColor; // RGB网格色，a混合强度
float4 _GridControl; // x开关，y重复频率，z单元阈值
float4 _LayerFeatures; // x备用颜色层，y屏幕抖动，z/w抖动响应
float4 _LayerScreenAndDepth; // xy源整数位模式尺寸，z预乘模式，w深度插值
float4 _DitherResolution; // 原cb尺寸位模式解码为可读像素数
Texture2D<float4> _UITexture3;

Texture2D<float4> _UITexture2;

Texture2D<float4> _UITexture1;

Texture2D<float4> _UITexture0;
















// 3Dmigoto declarations
#define cmp -


void SourceUI(float4 v0,float4 v1,float4 v2,float4 v3,float4 v4,float4 v5,out float4 o0) {
  float4 r0,r1,r2,r3;
  uint4 bitmask, uiDest;
  float4 fDest;

  r0.x = 255 * v1.w;
  r0.x = round(r0.x);
  r0.w = 0.00392156886 * r0.x;
  r1.xyzw = _UITexture0.Sample(_UISampler0, v2.xy).xyzw;
  r2.x = cmp(0.000000 != _TextureAlphaOverride.x);
  r1.w = r2.x ? 1 : r1.w;
  r1.xyzw = _TextureSampleAdd.xyzw + r1.xyzw;
  r0.xyz = v1.xyz;
  r2.xyzw = r1.xyzw * r0.xyzw;
  r0.yz = cmp(float2(0.5,0.5) < _LayerFeatures.xy);
  if (r0.y != 0) {
    r2.xyz = _UITexture3.Sample(_UISampler3, v2.xy).xyz;
    r2.w = -r0.x * r1.x + 1;
  }
  r0.x = cmp(0.5 < _PatternControl.z);
  if (r0.x != 0) {
    r0.xy = v3.xy * _PatternUVTransform.xy + _PatternUVTransform.zw;
    r0.xy = float2(200,200) * r0.xy;
    r0.xyw = _UITexture2.Sample(_UISampler2, r0.xy).xyz;
    r0.xyw = float3(-1,-1,-1) + r0.xyw;
    r0.xyw = _PatternControl.xxx * r0.xyw + float3(1,1,1);
    r0.xyw = _PatternControl.yyy * r0.xyw;
    r2.xyz = saturate(r2.xyz * r0.xyw);
  }
  r0.x = cmp(0.5 < _GridControl.x);
  r0.yw = _GridControl.yy * v2.xy;
  r1.xy = cmp(r0.yw >= -r0.yw);
  r0.yw = frac(abs(r0.yw));
  r0.yw = r1.xy ? r0.yw : -r0.yw;
  r0.yw = r0.yw * float2(2,2) + float2(-1,-1);
  r0.yw = -_GridControl.zz + abs(r0.yw);
  r1.xy = saturate(r0.yw);
  r1.x = r1.x * r1.y;
  r1.y = _GridControl.z * _GridControl.z;
  r0.yw = ceil(r0.yw);
  r0.y = -r0.y * r0.w + 1;
  r0.w = ceil(r1.x);
  r1.x = saturate(_GridControl.z * _GridControl.z + -r1.x);
  r0.w = r1.x * r0.w;
  r1.x = max(0.00100000005, r1.y);
  r0.w = r0.w / r1.x;
  r0.y = r0.y + r0.w;
  r0.w = _GridColor.w * r0.y;
  r0.y = -r0.y * _GridColor.w + 1;
  r1.xyz = _GridColor.xyz * r0.www;
  r1.xyz = r2.xyz * r0.yyy + r1.xyz;
  r0.xyw = r0.xxx ? r1.xyz : r2.xyz;
  if (r0.z != 0) {
    r1.xy = v5.xy / v5.ww;
    r1.zw = _DitherResolution.xy;
    r1.xy = r1.xy * r1.zw;
    r1.xy = float2(0.25,0.25) * r1.xy;
    r0.z = _UITexture1.Sample(_UISampler1, r1.xy).x;
    r1.x = _LayerFeatures.w * r0.z;
    r0.z = 3.14159274 * r0.z;
    r0.z = r1.x * _LayerFeatures.z + r0.z;
    r0.z = sin(r0.z);
    r1.x = 1 + -r0.z;
    r0.z = _LayerFeatures.z * r1.x + r0.z;
    r2.w = r2.w * r0.z;
  }
  r0.z = cmp(0.5 < _LayerScreenAndDepth.z);
  r1.x = cmp(r0.y >= r0.w);
  r1.x = r1.x ? 1.000000 : 0;
  r1.y = r0.y + -r0.w;
  r1.x = r1.x * r1.y + r0.w;
  r1.y = cmp(r0.x >= r1.x);
  r1.y = r1.y ? 1.000000 : 0;
  r1.z = -r1.x + r0.x;
  r1.x = r1.y * r1.z + r1.x;
  r1.y = r1.x + r1.x;
  r3.xyz = r2.www * r0.xyw;
  r0.x = r1.x * 2 + -1;
  r0.y = cmp(0 < r0.x);
  r0.x = cmp(r0.x < 0);
  r0.x = (int)-r0.y + (int)r0.x;
  r0.x = (int)r0.x;
  r0.x = cmp(r0.x < 0);
  r0.y = -r1.x * 2 + 2;
  r0.y = max(0.00999999978, r0.y);
  r0.x = r0.x ? r1.y : r0.y;
  r0.y = 1 + -r2.w;
  r0.w = 1 + -r0.x;
  r0.x = r0.y * r0.w + r0.x;
  r3.w = 1 + -r0.x;
  r2.xyz = r3.xyz;
  r0.xyzw = r0.zzzz ? r3.xyzw : r2.xyzw;
  o0.w = _AlphaReduction * -r0.w + r0.w;
  o0.xyz = r0.xyz;
  return;
}
struct UIInput { float4 clip:POSITION; float4 o1:COLOR; float4 o2:TEXCOORD0;float4 o3:TEXCOORD1;float4 o4:TEXCOORD2;float4 o5:TEXCOORD3;float4 o6:TEXCOORD4;float4 o7:TEXCOORD5;float4 o8:TEXCOORD6;float4 o9:TEXCOORD7; };
struct UIVaryings { float4 position:SV_POSITION;float4 o1:TEXCOORD0;float4 o2:TEXCOORD1;float4 o3:TEXCOORD2;float4 o4:TEXCOORD3;float4 o5:TEXCOORD4;float4 o6:TEXCOORD5;float4 o7:TEXCOORD6;float4 o8:TEXCOORD7;float4 o9:TEXCOORD8; };
UIVaryings UIVertex(UIInput i) { UIVaryings o; o.position=float4(i.clip.x,-i.clip.y*_EndfieldOutputScaleBias.y,i.clip.zw);o.o1=i.o1;o.o2=i.o2;o.o3=i.o3;o.o4=i.o4;o.o5=i.o5;o.o6=i.o6;o.o7=i.o7;o.o8=i.o8;o.o9=i.o9;return o;}
float4 UIFragment(UIVaryings i):SV_Target {float4 color=0; SourceUI(i.position,i.o1,i.o2,i.o3,i.o4,i.o5,color);return color;}
ENDHLSL
} } }