#ifndef ENDFIELD_ANALYTIC_SURFACE_LIGHTING_INCLUDED
#define ENDFIELD_ANALYTIC_SURFACE_LIGHTING_INCLUDED
// Typhon2 LitSurface/Graph16:2034-2054。此家族没有Ramp贴图，t10是POM高度图。
// 原G119.x=1，关闭额外的相机/光水平夹角修形；保留解析阈值1/4、跨度3/4。
float EFSourceAnalyticTransition(float cosine)
{
    float response = max((clamp(cosine,-1,1)-0.25)*(4.0/3.0),0);
    return response*response*(3-2*response);
}

float EFSourceAnalyticVisibility(EFSurface surface, float3 positionWS, float shadow,
    out float lightTransition, out float cameraTransition, out float materialVisibility)
{
    float3 cameraBack = unity_MatrixV[2].xyz;
    lightTransition = EFSourceAnalyticTransition(dot(surface.normalWS,SafeNormalize(_MainLightDirection.xyz))+_SourceRampBias);
    cameraTransition = EFSourceAnalyticTransition(dot(surface.normalWS,cameraBack));
    // 源t15.b（不是AO约定）限制明暗混合，角色t3.g由动态角色阴影producer替代。
    materialVisibility = shadow*surface.occlusion;
    return min(lightTransition,min(surface.occlusion,shadow));
}

float3 EFSourceAnalyticMainLighting(EFSurface surface, EFVaryings input, float3 indirectAlbedo,
    float shadow, out float3 mainDiffuse, out float3 mainSpecularRadiance)
{
    float lightTransition,cameraTransition,materialVisibility;
    float visible = EFSourceAnalyticVisibility(surface,input.positionWS,shadow,lightTransition,cameraTransition,materialVisibility);
    // Graph16:2057-2091：几何半球、SH色和源环境响应三段组合。
    float hemisphere = saturate(dot(normalize(input.normalWS),_SourceHemisphereDirection.xyz)+_SourceHemisphereParams.x);
    hemisphere = hemisphere*_SourceHemisphereParams.y+_SourceHemisphereParams.z;
    float3 ambient = EFUnityAmbient(surface.normalWS)*_SourceAmbientTint.rgb;
    float3 shade = lerp(ambient,1,visible*_SourceShadowStrength)*hemisphere;
    float response = clamp(_SourceAmbientResponse,0,1.5);
    float3 radiance = _MainLightColor.rgb*_SourceDirectTint.rgb;
    float3 sourceColor = radiance/max(max(radiance.r,max(radiance.g,radiance.b)),0.0001);
    float luminance = dot(radiance,float3(0.212673,0.715152,0.072175));
    float3 diffuseLighting = (shade*response*lerp(1,sourceColor,_SourceDirectColorWeight)+lerp(luminance.xxx,radiance,visible))*_SourceDiffuseStrength;

    // Graph16:2098-2171：背光基础色先作0.65/1.2亮度饱和响应，然后按解析明暗和相机项混合。
    float3 diffuse,f0;
    float specularWeight=surface.specular;
    #if defined(EF_SOURCE_ANISOTROPIC)
        specularWeight=1+(_ClothAnisotropy.w-1)*surface.specular;
    #endif
    EFSourceMaterialEnergy(surface.baseColor,surface.metallic,specularWeight,diffuse,f0);
    float3 indirect = indirectAlbedo*(0.96*(1-surface.metallic))*_SourceIndirectStrength;
    float3 shadowColor = indirect*0.65;
    float shadowLuminance = dot(shadowColor,float3(0.212673,0.715152,0.072175));
    shadowColor = lerp(shadowLuminance.xxx,shadowColor,1.2);
    float3 materialColor = lerp(shadowColor,indirect,saturate(cameraTransition*materialVisibility+lightTransition));
    materialColor = lerp(materialColor,diffuse,visible);
    // 原先ratio为L/max(L,.001)，再clamp至[0,1.5]；没有额外Ramp色度乘色。
    float materialLuminance = dot(materialColor,float3(0.212673,0.715152,0.072175));
    materialColor *= clamp(materialLuminance/max(materialLuminance,0.001),0,1.5);
    mainDiffuse = diffuseLighting*materialColor;
    mainSpecularRadiance = diffuseLighting*lerp(_SourceIndirectStrength,1,visible)*(visible*0.5+0.5);
    float3 view = normalize(_WorldSpaceCameraPos-input.positionWS);
    float3 halfVector = EFSourceMainHalfVector(view,SafeNormalize(_MainLightDirection.xyz));
    float specular = EFSourceSpecularLobe(surface.roughness,saturate(dot(surface.normalWS,halfVector)),saturate(dot(surface.normalWS,view)));
    float3 specularColor=f0*specular;
    #if defined(EF_SOURCE_ANISOTROPIC)
        specularColor=EFSourceClothSpecular(surface,input.normalWS,input.tangentWS,view,halfVector,f0);
    #endif
    return mainDiffuse+mainSpecularRadiance*specularColor*_SourceSpecularStrength;
}
#endif
