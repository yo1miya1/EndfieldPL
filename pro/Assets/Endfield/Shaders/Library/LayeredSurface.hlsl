#ifndef ENDFIELD_LAYERED_SURFACE_INCLUDED
#define ENDFIELD_LAYERED_SURFACE_INCLUDED
#include "Surface.hlsl"
#include "SourceCharacterLighting.hlsl"
#include "SourceOutline.hlsl"

// 可选叶的语义参数只属于分层材质，不改变既有材质默认路径。
#if defined(EF_LAYER_MASKED_INDIRECT) || defined(EF_LAYER_UV1_TINT)
TEXTURE2D(_LayerResponseMap); SAMPLER(sampler_LayerResponseMap);
float4 _LayerIndirectRange,_LayerIndirectTint;
float4 _LayerTintUv,_LayerTintColor,_LayerTintAxis,_LayerTintResponse,_LayerTintControls;
float4 _LayerObjectOrigin; float _LayerInstanceCut;
#endif
// 仅材质叶函数不同；灯光、探针和角色局部可见性继续走公共动态Unity接口。
EFVaryings EFLayeredSurfaceVertex(EFAttributes input)
{
    #if defined(EF_LAYER_OUTLINE)
        return EFSourceOutlineVertex(input);
    #else
        return EFVertex(input);
    #endif
}

float4 EFLayeredSurfaceFragment(EFVaryings input,bool frontFace:SV_IsFrontFace):SV_Target
{
    float layerPlane=0;
    #if defined(EF_LAYER_UV1_TINT)
        // OutlineSurface UV1叶：源世界平面已在发布边界减场景原点；运行继续使用实际world。
        float2 chosenUv=_LayerTintControls.x!=0 ? input.uv1:input.uv;
        float2 viewUv=mul((float3x3)unity_MatrixV,input.positionWS-_LayerObjectOrigin.xyz).xy;
        float2 maskUv=lerp(chosenUv,viewUv,_LayerTintResponse.x)*_LayerTintUv.xy+_LayerTintUv.zw;
        float mask=SAMPLE_TEXTURE2D_BIAS(_LayerResponseMap,sampler_LayerResponseMap,maskUv,_SourceMipBias).r;
        float threshold=max(_LayerTintResponse.z,_LayerInstanceCut)*2.02-1.01;
        layerPlane=(_LayerTintControls.z-dot(input.positionWS,_LayerTintAxis.xyz))*_LayerTintControls.y
            +(mask-threshold)*_LayerTintControls.w;
        clip(saturate(layerPlane*_LayerTintResponse.y)-.01);
    #endif
    float4 base=SAMPLE_TEXTURE2D_BIAS(_BaseMap,sampler_BaseMap,input.uv,_SourceMipBias)*_BaseColor;
    EFGBufferOutput g=EFSourceCharacterGBuffer(input,frontFace,0);
    EFSurface s=EFSampleSurface(input,frontFace);
    s.normalWS=EFDecodeNormal(g.target3.xy);
    s.baseColor=g.target4.rgb;
    float3 indirect=s.baseColor;
    #if defined(EF_LAYER_OUTLINE)
        // OutlineSurface/LayeredLookupOutline叶：先增益与饱和度，再按源开关选固定轮廓色。
        float3 layered=base.rgb*_EffectColorIntensity;
        float luminance=dot(layered,float3(.212673,.715152,.072175));
        s.baseColor=lerp(luminance.xxx,layered,_EffectColorResponse.w);
        #if defined(EF_LAYER_COLOR_OVERRIDE)
            s.baseColor=_OutlineColor.rgb;
        #endif
        // 源outline图在增益/饱和度/固定色选择后才建立间接输入，不能绕过增益再用原base。
        indirect=s.baseColor;
        s.metallic=0;
        s.specular=0;
        s.roughness=1;
    #elif defined(EF_SOURCE_PACKED_MASK)
        float4 mask=SAMPLE_TEXTURE2D_BIAS(_SourceMaskMap,sampler_SourceMaskMap,input.uv,_SourceMipBias);
        s.metallic=mask.r;
        s.specular=mask.g;
        s.roughness=1-mask.a;
    #endif
    #if defined(EF_LAYER_INDIRECT_RESPONSE)
        indirect*=_SourceIndirectAlbedoGain;
        float indirectLuminance=dot(indirect,float3(.212673,.715152,.072175));
        indirect=lerp(indirectLuminance.xxx,indirect,_SourceIndirectSaturation);
    #endif
    #if defined(EF_SOURCE_COLOR_LUT)
        indirect=EFSourceAlbedoResponse(indirect);
    #endif
    float3 shadowN=EFDecodeNormal(round(EFEncodeNormal(s.normalWS)*1023)/1023);
    float shadow=EFCharacterShadow(input.positionWS,shadowN,input.positionCS.xy,(int)_CharacterShadowIndex);
    float3 diffuse,specularRadiance;
    float3 color=EFSourceMainLighting(s,input,indirect,shadow,diffuse,specularRadiance);
    float3 view=normalize(_WorldSpaceCameraPos-input.positionWS);
    #if defined(EF_SOURCE_ENVIRONMENT_REFLECTION)
        float3 diffuseEnergy,f0;
        EFSourceMaterialEnergy(s.baseColor,s.metallic,s.specular,diffuseEnergy,f0);
        color+=EFSourceEnvironmentSpecular(s.normalWS,view,input.positionWS,s.roughness,f0)*_SourceEnvironmentStrength;
    #endif
    #if defined(EF_LAYER_MASKED_INDIRECT)
        float response=SAMPLE_TEXTURE2D_BIAS(_LayerResponseMap,sampler_LayerResponseMap,input.uv,_SourceMipBias).r;
        float amount=lerp(_LayerIndirectRange.y,_LayerIndirectRange.x,response);
        // 动态受光/可见性来自公共路径；此处只保留材质自己的颜色响应。
        float facing=1-(saturate(dot(s.normalWS,view))*.85+.15);
        color*=lerp(1,_LayerIndirectTint.rgb,saturate(amount*facing));
    #endif
    #if defined(EF_LAYER_UV1_TINT)
        color+=_LayerTintColor.rgb*saturate((_LayerTintResponse.w-layerPlane)*_LayerTintResponse.y)*_SourceAmbientResponse;
    #endif
    color=EFSourceAdditionalLighting(s,input,color);
    float alpha=saturate(base.a*_EffectOpacity);
    #if defined(EF_LAYER_ALPHA_CLIP)
        clip(alpha-_Cutoff);
    #endif
    #if defined(EF_LAYER_PREMULTIPLIED)
        color*=alpha;
    #endif
    return float4(max(color,0),alpha);
}
#endif
