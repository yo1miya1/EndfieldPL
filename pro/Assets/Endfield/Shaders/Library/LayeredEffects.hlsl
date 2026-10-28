#ifndef ENDFIELD_LAYERED_EFFECTS_INCLUDED
#define ENDFIELD_LAYERED_EFFECTS_INCLUDED
#include "Coordinates.hlsl"
#include "Shadows.hlsl"
#include "CharacterShadows.hlsl"

TEXTURE2D(_BaseMap); SAMPLER(sampler_BaseMap);
TEXTURECUBE(_SkyMap); SAMPLER(sampler_SkyMap);
TEXTURE2D(_CameraDepthTexture); SAMPLER(sampler_PointClamp);
TEXTURE2D(_GBuffer3);
CBUFFER_START(UnityPerMaterial)
float4 _BaseColor, _UVTransform, _UVRotation, _UVVelocity, _UVWeights;
float4 _DepthRanges, _DissolveProfile, _DissolveColor, _ColorResponse, _SkyRotation;
float4 _ShadowTint, _SecondaryShadowTint, _ShadowRange, _ShadowOrigin;
float _Model, _IgnoreVertexColor, _ColorGain, _AlphaGain, _MonochromeWeight, _MipBias;
float _Opacity, _Cutoff, _BloomThreshold, _BloomBoost, _PreExposureWeight;
float _DepthFadeEnabled, _DissolveEnabled, _DissolveMask, _DissolveHeight, _ResponseWeight;
float _AlphaMode, _InvisibleWeight, _UVStreamBlend, _Phase, _PhaseSpeed;
float _ViewOffset, _ViewOffsetWeight, _RibbonWidth, _ForceNearPlane, _FilterInfluence, _FilterOpacity;
float _FilterRejectMaterialTag;
float _Cull, _ZWrite, _ZTest, _SrcBlend, _DstBlend, _SrcBlendAlpha, _DstBlendAlpha, _BlendOp, _BlendOpAlpha;
float _StencilRef, _StencilReadMask, _StencilWriteMask, _StencilComp, _StencilPass, _StencilFail, _StencilZFail;
CBUFFER_END
float _EndfieldSceneExposure;
float4 _Time;

struct EFLayerAttributes
{
    float3 positionOS:POSITION;
    float3 normalOS:NORMAL;
    float4 color:COLOR;
    float2 uv:TEXCOORD0;
    float4 extra0:TEXCOORD3;
    float4 extra1:TEXCOORD4;
    float4 extra2:TEXCOORD5;
};
struct EFLayerVaryings
{
    float4 positionCS:SV_POSITION;
    float3 world:TEXCOORD0;
    float3 normal:TEXCOORD1;
    float4 uv:TEXCOORD2;
    float4 color:TEXCOORD3;
    float3 direction:TEXCOORD4;
};

EFLayerVaryings EFLayerVertex(EFLayerAttributes input)
{
    EFLayerVaryings output;
    output.world=EFWorldPosition(input.positionOS);
    output.normal=EFWorldNormal(input.normalOS);
    output.positionCS=EFClipPosition(output.world);
    output.color=lerp(input.color,1,_IgnoreVertexColor);
    float phase=_Phase+_Time.y*_PhaseSpeed;
    float2 uv=input.uv;
    if (_Model==1) // 带时间UV的分层效果：animated_uv/VaryingAbi23。
    {
        float4 pair=lerp(input.extra1.xxyy,input.extra0.zzww,_UVStreamBlend);
        pair=pair*_UVWeights.y+input.extra0.xxyy*_UVWeights.x;
        pair+=_UVVelocity.xxyy*phase+_UVVelocity.zzww*(input.extra1.x*_UVStreamBlend);
        pair=(pair-.5)*_UVRotation;
        uv=(pair.xy+pair.zw+.5)*_UVTransform.xy+_UVTransform.zw;
        output.uv.zw=input.extra1.zw*_UVStreamBlend;
        float3 ray=_WorldSpaceCameraPos-output.world;
        float distance=length(ray);
        output.world+=ray/distance*(.001+min(_ViewOffset,max(0,distance-1)))*_ViewOffsetWeight;
        output.positionCS=EFClipPosition(output.world);
    }
    else if (_Model==2) // CameraFacingRibbon：源世界pivot由发布器减场景原点。
    {
        float3 pivot=EFWorldPosition(input.extra2.xyz);
        float3 facing=normalize(_WorldSpaceCameraPos-pivot);
        float3 side=normalize(cross(output.normal,facing));
        float2 projected=normalize(mul(unity_MatrixVP,float4(side,0)).xy)*float2(_ScreenParams.y/_ScreenParams.x,1)*_RibbonWidth;
        float minimum=.75/min(_ScreenParams.x,_ScreenParams.y)*output.positionCS.w;
        float2 offset=projected*.01;
        offset=float2(abs(offset.x)<minimum ? sign(projected.x)*minimum:offset.x,
            abs(offset.y)<minimum ? sign(projected.y)*minimum:offset.y);
        output.positionCS.xy+=offset;
        if (_ForceNearPlane!=0) output.positionCS.z=0;
        uv=lerp(input.extra0.xy,lerp(input.extra1.xy,input.extra0.zw,_UVStreamBlend),_UVWeights.x);
        uv+=_UVVelocity.xy*phase+_UVVelocity.zw*(input.extra1.x*_UVStreamBlend);
        float2 p=uv-.5;
        uv=float2(dot(p,_UVRotation.xy),dot(p,_UVRotation.zw))+.5;
        uv=uv*_UVTransform.xy+_UVTransform.zw;
    }
    else if (_Model==3 || _Model==4)
    {
        uv=input.extra0.xy*_UVTransform.xy+_UVTransform.zw;
        // 视图偏移采用当前投影焦距，不保存捕获相机矩阵或抖动。
        output.positionCS.x-=length(unity_MatrixVP[0].xyz)*_ViewOffset*_ViewOffsetWeight;
    }
    else uv=uv*_UVTransform.xy+_UVTransform.zw;
    output.uv.xy=uv;
    output.direction=input.extra0.xyz;
    if (_Model==5) output.positionCS.z=0; // 源天空在反Z远平面绘制。
    return output;
}

float EFEffectDepthFade(float3 world)
{
    if (_DepthFadeEnabled==0) return 1;
    float depth=abs(mul(unity_MatrixV,float4(world,1)).z);
    return saturate((depth-_DepthRanges.x)/(_DepthRanges.y-_DepthRanges.x))
        *saturate((depth-_DepthRanges.z)/(_DepthRanges.w-_DepthRanges.z));
}

float4 EFLayerFragment(EFLayerVaryings input):SV_Target
{
    if (_Model==4) return 0; // 源DepthOnlyOverlay颜色保持，深度/Stencil由固定状态处理。
    if (_Model==5)
    {
        float3 d=input.direction;
        d.xz=float2(dot(d.xz,_SkyRotation.xy),dot(d.xz,_SkyRotation.zw));
        return float4(SAMPLE_TEXTURECUBE(_SkyMap,sampler_SkyMap,d).rgb*_BaseColor.rgb*_ColorGain,1);
    }
    if (_Model==6)
    {
        float visibility=EFMainShadow(input.world);
        [loop] for(int index=0;index<_CharacterShadowCount;index++)
            visibility=min(visibility,EFCharacterShadow(input.world,normalize(input.normal),input.positionCS.xy,index));
        float coverage=saturate(.95-visibility)*_ShadowTint.a;
        if (_ShadowRange.z!=0)
        {
            float distance=length(input.world-EFWorldPosition(_ShadowOrigin.xyz));
            float t=saturate((distance-_ShadowRange.x-_ShadowRange.y)/(-_ShadowRange.y));
            coverage*=t*t*(3-2*t);
        }
        // SharedEnvironment/SurfaceFormula02最终是乘法阴影色，而非第二次照亮底图。
        return float4(lerp(1,_ShadowTint.rgb,coverage),1);
    }
    float4 sampled=SAMPLE_TEXTURE2D_BIAS(_BaseMap,sampler_BaseMap,input.uv.xy,_MipBias);
    if (_Model==7) // MotionUvSurface：实际激活的预乘颜色/覆盖率路径，深度与运动另由管线生成。
    {
        float4 value=sampled*_BaseColor;
        float alpha=lerp(value.a,value.r*value.a,_AlphaMode);
        clip(alpha-_Cutoff);
        return float4(clamp(value.rgb*value.a,0,1000),saturate(alpha));
    }
    sampled=lerp(sampled,float4(1,1,1,sampled.r),_MonochromeWeight);
    float4 color=sampled*input.color*_BaseColor*float4(_ColorGain.xxx,_AlphaGain);
    color*=1-_InvisibleWeight;
    if (_DissolveEnabled!=0)
    {
        float influence=_DissolveMask*_DissolveHeight;
        float mask=1-influence;
        float edge=mask*((input.uv.z+_DissolveProfile.y)*2.02-.01)-1;
        float a=saturate(-edge*_DissolveProfile.x);
        float rim=saturate((edge+_DissolveProfile.z)*_DissolveProfile.x);
        color.rgb=lerp(color.rgb,_DissolveColor.rgb*_ColorGain,rim*rim);
        color.a*=a;
    }
    if (_Model==3)
    {
        float influence=_FilterInfluence*_FilterOpacity;
        float3 tinted=lerp(color.rgb,_ColorResponse.rgb,influence);
        float alpha=EFEffectDepthFade(input.world)*color.a*(1-influence);
        if (_FilterRejectMaterialTag!=0 && LOAD_TEXTURE2D(_GBuffer3,(uint2)input.positionCS.xy).a==1) alpha=0;
        return float4(lerp(1,tinted,alpha),alpha);
    }
    color.rgb+=max(color.rgb-_BloomThreshold,0)*_BloomBoost;
    color.rgb*=lerp(1,_EndfieldSceneExposure,_PreExposureWeight);
    color.rgb=clamp(color.rgb,0,1000);
    float alpha=saturate(color.a*EFEffectDepthFade(input.world))*_Opacity;
    clip(alpha-_Cutoff);
    float3 premultiplied=color.rgb*alpha;
    if (_Model==1 && _AlphaMode==2) premultiplied+=1-alpha;
    float luminance=dot(premultiplied,float3(.212673,.715152,.072175));
    float3 response=lerp(luminance.xxx,premultiplied,_ColorResponse.w)*_ColorResponse.rgb;
    return float4(lerp(premultiplied,response,_ResponseWeight),_Model==1 ? alpha*max(1-_AlphaMode,0):alpha);
}
#endif
