#ifndef ENDFIELD_SOURCE_CHARACTER_LIGHTING_INCLUDED
#define ENDFIELD_SOURCE_CHARACTER_LIGHTING_INCLUDED
#include "Surface.hlsl"
#include "Lighting.hlsl"
#include "EnvironmentReflection.hlsl"
#include "ParallaxGlow.hlsl"
#include "SourceEye.hlsl"

// 原材质 LUT 的 B切片/R横轴/G纵轴，32³展开为1024×32；采样返回线性RGB。
// SI1 1019:39-55、1040:40-56；与旧LitSurface的同一片段直接重组。
float3 EFSourceAlbedoResponse(float3 linearColor)
{
    float3 srgb;
    float3 high = 1.055 * pow(abs(linearColor), 1.0 / 2.4) - 0.055;
    srgb = saturate(float3(linearColor.r <= 0.0031308 ? linearColor.r * 12.92 : high.r,
                          linearColor.g <= 0.0031308 ? linearColor.g * 12.92 : high.g,
                          linearColor.b <= 0.0031308 ? linearColor.b * 12.92 : high.b));
    float slice = floor(srgb.b * 31);
    float2 uv = float2(slice / 32 + srgb.r * (31.0 / 1024) + 0.5 / 1024, srgb.g * (31.0 / 32) + 0.5 / 32);
    float3 a = SAMPLE_TEXTURE2D_LOD(_AlbedoResponseLut, sampler_AlbedoResponseLut, uv, 0).rgb;
    float3 b = SAMPLE_TEXTURE2D_LOD(_AlbedoResponseLut, sampler_AlbedoResponseLut, uv + float2(1.0 / 32, 0), 0).rgb;
    return lerp(a, b, srgb.b * 31 - slice);
}

// 原材质能量划分：1019:993-999 / 997:971-979。
void EFSourceMaterialEnergy(float3 baseColor, float metallic, float specular, out float3 diffuse, out float3 f0)
{
    float diffuseWeight = 0.96 * (1 - metallic);
    diffuse = baseColor * diffuseWeight;
    f0 = lerp((0.04 * specular).xxx, baseColor, metallic);
}

// 源简化微表面分布/可见性：1019:999-1000及1122-1134。
// 保留最小alpha=1/128、可见性epsilon=2^-14和最大20；不同于标准GGX-Smith。
float EFSourceSpecularLobe(float roughness, float nh, float nv)
{
    float alpha = max(roughness * roughness, 0.0078125);
    float alphaSquared = alpha * alpha;
    float denominator = nh * nh * (alphaSquared - 1) + 1;
    denominator *= denominator;
    float distribution = denominator != alphaSquared ? alphaSquared / denominator : 1;
    float visibility = 0.5 / (2 * nv + alpha + 0.0001);
    return clamp(distribution * visibility - 0.00006103515625, 0, 20);
}

// 源1019:1084-1097 / 997:1082-1095 的Ramp色度分离与亮度恢复。
// 直接乘褐色Ramp会二次染红肤色；源程序只以色度调制后恢复原亮度。
float3 EFSourceRampPreserveLuminance(float3 inputColor, float3 ramp)
{
    float chroma = max(ramp.r, max(ramp.g, ramp.b)) - min(ramp.r, min(ramp.g, ramp.b));
    float3 rampColor = ramp * chroma + (1 - chroma);
    float3 modified = inputColor * rampColor;
    float luminance = dot(inputColor, float3(0.212673,0.715152,0.072175));
    float modifiedLuminance = max(dot(modified, float3(0.212673,0.715152,0.072175)), 0.001);
    float ratio = clamp(luminance / modifiedLuminance, 0, 1.5);
    return modified * ratio;
}

float EFSourceAnisotropicDistribution(float3 normal, float3 tangent, float3 bitangent, float3 halfVector, float alphaPositive, float alphaNegative)
{
    // 源1122:1153-1178 / 1649相同段，保留乘积三次方和相等时返回1的规则。
    float product = alphaPositive * alphaNegative;
    float3 stretched = float3(dot(tangent,halfVector) * alphaNegative,
                             dot(bitangent,halfVector) * alphaPositive,
                             dot(normal,halfVector) * product);
    float denominator = dot(stretched,stretched);
    denominator *= denominator;
    float numerator = product * product * product;
    return denominator != numerator ? numerator / denominator : 1;
}

void EFSourceClothFrame(EFSurface s, float3 geometricNormal, float4 meshTangent, out float3 tangent, out float3 bitangent)
{
    // 源1122:59-75 / 1649同族：M13.x>=.5时由几何法线建立水平切线。
    float3 candidate = meshTangent.xyz;
    if (_ClothTangentMode >= 0.5)
        candidate = float3(-geometricNormal.z,0,geometricNormal.x) * rsqrt(max(dot(geometricNormal.xz,geometricNormal.xz),0.00006103515625));
    tangent = normalize(candidate-s.normalWS*dot(s.normalWS,candidate));
    bitangent = cross(s.normalWS,tangent)*meshTangent.w;
}

float3 EFSourceMainHalfVector(float3 view, float3 light)
{
    // 源1122:1138-1151 / 1082:729-743，当前屏幕AO边界为1时的主光半向量。
    float3 cameraDirection = unity_MatrixV[2].xyz;
    cameraDirection.y = light.y;
    return normalize(normalize(cameraDirection)*2+light+view*3);
}

float3 EFSourceClothSpecular(EFSurface s, float3 geometricNormal, float4 meshTangent, float3 view, float3 halfVector, float3 f0)
{
    float3 tangent,bitangent;
    EFSourceClothFrame(s,geometricNormal,meshTangent,tangent,bitangent);
    float3 secondHalf = normalize(halfVector + view * _ClothAnisotropy.z);
    float alpha = max(s.roughness * s.roughness,0.0078125);
    float4 widths = alpha * (1 + s.specular * float4(_ClothAnisotropy.xy,-_ClothAnisotropy.xy));
    float d1 = EFSourceAnisotropicDistribution(s.normalWS,tangent,bitangent,halfVector,widths.x,widths.z);
    float d2 = EFSourceAnisotropicDistribution(s.normalWS,tangent,bitangent,secondHalf,widths.y,widths.w);
    float nv = saturate(dot(s.normalWS,view));
    float visibility = 0.5 / (2 * nv + alpha + 0.0001);
    float primary = clamp(d1 * visibility - 0.00006103515625,0,20);
    float secondary = clamp(d2,0,20);
    return f0 * (primary + _ClothSecondLobeColor.rgb * s.specular * secondary);
}

float3 EFSourceDirect(EFSurface s, float3 positionWS, float3 direction, float3 radiance, float shadow, float3 geometricNormal, float4 tangentWS)
{
    float3 view = normalize(_WorldSpaceCameraPos - positionWS);
    float nl = dot(s.normalWS, direction);
    // 源Ramp采样输入保留half-Lambert+bias，不用任意smoothstep Toon近似。
    float rampU = clamp(nl + _SourceRampBias, -1, 1) * 0.5 + 0.5;
    float4 ramp = SAMPLE_TEXTURE2D_LOD(_LightingRamp, sampler_LightingRamp, float2(rampU, 0.5), 0);
    float3 diffuse, f0;
    float specularWeight = s.specular;
    #if defined(EF_SOURCE_ANISOTROPIC)
        specularWeight = 1 + (_ClothAnisotropy.w - 1) * s.specular;
    #endif
    EFSourceMaterialEnergy(s.baseColor, s.metallic, specularWeight, diffuse, f0);
    float nh = saturate(dot(s.normalWS, normalize(view + direction)));
    float specular = EFSourceSpecularLobe(s.roughness, nh, saturate(dot(s.normalWS,view)));
    float3 specularColor = f0 * specular;
    #if defined(EF_SOURCE_ANISOTROPIC)
        specularColor = EFSourceClothSpecular(s,geometricNormal,tangentWS,view,normalize(view+direction),f0);
    #endif
    // 原阴影/胶囊/SH色彩组合仍需接实时producer；此处仅替换入射可见性边界。
    float visibility = lerp(1, shadow, _SourceShadowStrength);
    float3 diffuseRamp = EFSourceRampPreserveLuminance(diffuse, ramp.rgb);
    // 源1019:1053-1074：半球明暗响应、阴影色向白色恢复、直射颜色的亮度/彩色混合。
    // 本帧3D SH关闭，原fallback环境色通过Unity ambientProbe和材质风格乘色提供。
    float rampVisibility = min(ramp.a, visibility);
    float hemisphere = saturate(dot(s.normalWS, _SourceHemisphereDirection.xyz) + _SourceHemisphereParams.x);
    hemisphere = hemisphere * _SourceHemisphereParams.y + _SourceHemisphereParams.z;
    float3 sourceAmbient = EFUnityAmbient(s.normalWS) * _SourceAmbientTint.rgb;
    float3 shadeTint = lerp(sourceAmbient, 1, rampVisibility);
    float radianceLuminance = dot(radiance, float3(0.212673,0.715152,0.072175));
    float3 radianceResponse = lerp(radianceLuminance.xxx, radiance, rampVisibility);
    float3 diffuseRadiance = shadeTint * hemisphere * radiance + radianceResponse;
    // 源Ramp的A独立承担明暗可见性，RGB不是另一份能量衰减。
    return (diffuseRamp * ramp.a * _SourceDiffuseStrength * diffuseRadiance + specularColor * _SourceSpecularStrength * radiance) * visibility;
}

// SI1_1019:1035-1106及1082:560/674-728的主光漫反与间接色组合。
// 两家族共享此算术段，但1082另有面部SDF/区域Mask输入，不能据此视作整份PS相同。
float3 EFSourceMainLighting(EFSurface s, EFVaryings input, float3 indirectAlbedo,
    float characterShadow, out float3 mainDiffuse, out float3 mainSpecularRadiance)
{
    float3 view = normalize(_WorldSpaceCameraPos - input.positionWS);
    float3 light = SafeNormalize(_MainLightDirection.xyz);
    float rampU = clamp(dot(s.normalWS,light) + _SourceRampBias,-1,1) * 0.5 + 0.5;
    #if defined(EF_SOURCE_SKIN)
        // SI1_1082:562-654 / 1101同族：面部双侧SDF与普通法线受光按区域G混合。
        float4 skinRegion = SAMPLE_TEXTURE2D_BIAS(_SkinRegionMap,sampler_SkinRegionMap,input.uv,_SourceMipBias);
        float3 right = EFWorldTangent(_SkinRightOS.xyz);
        float3 forward = EFWorldTangent(_SkinForwardOS.xyz);
        float2 localLight = normalize(float2(dot(light,right),dot(light,forward)));
        float2 sdfUV = float2(localLight.x > 0 ? input.uv.x : 1-input.uv.x,input.uv.y);
        float4 skinSdf = SAMPLE_TEXTURE2D_LOD(_SkinLightingSdf,sampler_SkinLightingSdf,sdfUV,0);
        float sdfCosine = clamp(localLight.y + _SkinSdfBias,-1,1);
        float threshold = clamp(0.5-0.5*sdfCosine,0.001,0.999);
        float lower = max(2*threshold-1,0);
        float interval = min(2*threshold,1)-lower;
        float smoothSdf = saturate(((skinSdf.r+skinSdf.g)*0.5-lower)/interval);
        smoothSdf = smoothSdf*smoothSdf*(3-2*smoothSdf);
        float halfCosine = 0.5*sdfCosine;
        float sdfSigned = 2*abs(-smoothSdf-halfCosine*ceil(halfCosine))-1;
        float normalSigned = clamp(dot(s.normalWS,light)+_SourceRampBias,-1,1);
        rampU = lerp(sdfSigned,normalSigned,skinRegion.g)*0.5+0.5;
    #endif
    float4 ramp = SAMPLE_TEXTURE2D_LOD(_LightingRamp,sampler_LightingRamp,float2(rampU,0.5),0);
    float shadow = characterShadow;
    #if defined(EF_SOURCE_SKIN)
        // 源1082:359/662-673：相机局部XZ前向的侧向过渡，只由真实区域B/G控制。
        float3 cameraBack = unity_MatrixV[2].xyz;
        float2 localCamera = normalize(float2(dot(cameraBack,right),dot(cameraBack,forward)));
        float sideOcclusion = saturate((localCamera.y-0.75)*-2);
        sideOcclusion = sideOcclusion*sideOcclusion*(3-2*sideOcclusion);
        float shadowWeight = max(skinRegion.b*sideOcclusion,skinRegion.g);
        shadow = lerp(1,shadow,shadowWeight);
    #endif
    float visible = min(ramp.a,shadow);
    #if defined(EF_SOURCE_SKIN)
        visible = min(s.alpha,visible);
    #endif
    float3 sourceAmbient = EFUnityAmbient(s.normalWS) * _SourceAmbientTint.rgb;
    float3 shade = lerp(sourceAmbient,1,visible * _SourceShadowStrength);
    // 半球输入按源家族选择：默认几何法线；Hair用主法线图，1019用水平法线，1082/1101用区域混合。
    float3 hemisphereNormal = normalize(input.normalWS);
    #if defined(EF_HAIR)
        // 1165 PS78保存主法线图结果到r16，1121直接以r16参与半球响应。
        hemisphereNormal = s.normalWS;
    #endif
    #if defined(EF_SOURCE_VIEW_TINT) && !defined(EF_SOURCE_SKIN)
        // 1019 PS93-96/1053：身体皮肤用扰动N的水平投影，不读取几何法线Ny。
        hemisphereNormal = normalize(float3(s.normalWS.x,0.00006103515625,s.normalWS.z));
    #endif
    #if defined(EF_SOURCE_SKIN)
        // 源1082:35-39/129-136。面部采用半球中心的水平径向，身体G区切换到水平法线。
        float3 radial = input.positionWS-EFWorldPosition(_SkinHemisphereOriginOS.xyz);
        radial.y = 0.00006103515625;
        float3 horizontalNormal = float3(s.normalWS.x,0.00006103515625,s.normalWS.z);
        hemisphereNormal = normalize(lerp(normalize(radial),normalize(horizontalNormal),skinRegion.g));
    #endif
    float hemisphere = saturate(dot(hemisphereNormal,_SourceHemisphereDirection.xyz) + _SourceHemisphereParams.x);
    shade *= hemisphere * _SourceHemisphereParams.y + _SourceHemisphereParams.z;
    float response = _SourceAmbientResponse;
    float3 radiance = _MainLightColor.rgb;
    float radianceLuminance = dot(radiance,float3(0.212673,0.715152,0.072175));
    float3 coloredRadiance = lerp(radianceLuminance.xxx,radiance,visible);
    // 引擎Light把颜色与强度相乘；源色彩因子为其归一化颜色，辐照度保留完整强度。
    float3 lightColor = radiance / max(max(radiance.r,max(radiance.g,radiance.b)),0.0001);
    float3 diffuseLighting = (shade * min(max(response,0),1.5) * lerp(1,lightColor,_SourceDirectColorWeight) + coloredRadiance) * _SourceDiffuseStrength;
    // 当前无独立屏幕AO producer，此边界为1；Unity主光阴影继续影响visible，不能再整项乘shadow。
    float3 diffuse, f0;
    float specularWeight = s.specular;
    #if defined(EF_SOURCE_ANISOTROPIC)
        specularWeight = 1 + (_ClothAnisotropy.w-1)*s.specular;
    #endif
    EFSourceMaterialEnergy(s.baseColor,s.metallic,specularWeight,diffuse,f0);
    float3 indirectDiffuse = indirectAlbedo * (0.96*(1-s.metallic)) * _SourceIndirectStrength;
    float3 shadowResponse = indirectDiffuse * 0.65;
    float shadowLuminance = dot(shadowResponse,float3(0.212673,0.715152,0.072175));
    shadowResponse = lerp(shadowLuminance.xxx,shadowResponse,1.2);
    float3 materialResponse = lerp(shadowResponse,indirectDiffuse,saturate(shadow+ramp.a));
    materialResponse = lerp(materialResponse,diffuse,visible);
    materialResponse = EFSourceRampPreserveLuminance(materialResponse,ramp.rgb);
    float specularVisibility = lerp(_SourceIndirectStrength,1,visible) * (visible * 0.5 + 0.5);
    float3 halfVector = EFSourceMainHalfVector(view,light);
    float3 specularColor = f0*EFSourceSpecularLobe(s.roughness,saturate(dot(s.normalWS,halfVector)),saturate(dot(s.normalWS,view)));
    #if defined(EF_SOURCE_ANISOTROPIC)
        specularColor = EFSourceClothSpecular(s,input.normalWS,input.tangentWS,view,halfVector,f0);
    #endif
    float3 directSpecular = specularColor*_SourceSpecularStrength;
    #if defined(EF_SOURCE_SKIN)
        // 源1082:749-752/784-787的独立高光图，当前视线在解剖右/上轴产生UV偏移。
        float3 skinUp = normalize(cross(forward,right));
        float2 specularUV = input.uv+float2(dot(view,right),dot(view,skinUp))*_SkinSpecularParallax.xy;
        float3 skinSpecular = SAMPLE_TEXTURE2D_BIAS(_SkinSpecularMap,sampler_SkinSpecularMap,specularUV,_SourceMipBias).rgb;
        directSpecular += skinSpecular;
    #endif
    mainDiffuse = diffuseLighting*materialResponse;
    mainSpecularRadiance = diffuseLighting*specularVisibility;
    return mainDiffuse+mainSpecularRadiance*directSpecular;
}

// SI1_1165:1197-1213/1252-1269 的双发丝高光核。
// 原主瓣指数200，次瓣指数向零取整；颜色由真实源Ramp/材质色决定。
float3 EFSourceHairSpecular(float3 normal, float3 tangent, float3 halfVector, float4 mask, float visibility, out float primaryMaximum)
{
    float3 primaryTangent = normalize(tangent + normal * (_HairPrimarySecondaryShift.x * 2 - 1));
    float3 secondaryTangent = normalize(tangent + normal * (_HairPrimarySecondaryShift.y * 2 - 1));
    float primaryTH = dot(primaryTangent, halfVector);
    float primary = saturate(mask.g * pow(max(sqrt(saturate(1 - primaryTH * primaryTH)), 0.0001), 200));
    float rampY = visibility * visibility * (primaryTH > 0 ? 1 : 0);
    float3 primaryColor = SAMPLE_TEXTURE2D_LOD(_HairSpecularRamp, sampler_HairSpecularRamp, float2(primary, rampY), 0).rgb;
    primaryColor *= primary * visibility;
    float secondaryTH = dot(secondaryTangent, halfVector);
    float secondaryExponent = trunc(max(1 - _HairSecondarySmoothness, 0) * 200);
    float secondary = pow(max(sqrt(saturate(1 - secondaryTH * secondaryTH)), 0.0001), secondaryExponent) * visibility;
    float primaryMax = max(primaryColor.r, max(primaryColor.g, primaryColor.b));
    primaryMaximum = primaryMax;
    float3 secondaryColor = mask.a * _HairSecondaryColor.rgb * secondary * (1 - primaryMax);
    // 源1165:1249-1267：主瓣还乘介质F0与环境响应，次瓣也乘环境响应。
    // 漏掉.04*maskG会把原本柔和的发丝反射放大数十倍。
    return (primaryColor * (0.04 * mask.g) * _HairPrimaryStrength * 5 + secondaryColor) * _SourceAmbientResponse;
}

float3 EFSourceHairDiffuseOcclusion(float3 diffuse, float3 detailNormal, float3 strand, float3 halfVector, float2 uv, float maskG, float primaryMaximum)
{
    // 源1165:1219-1248第三瓣遮蔽，不是额外高光或任意AO。
    float3 occlusionTangent = normalize(strand+detailNormal*(_HairOcclusionLobe.y*2-1));
    float th = dot(occlusionTangent,halfVector);
    float exponent = trunc(max(1-_HairOcclusionLobe.z,0)*200);
    float lobe = pow(max(sqrt(saturate(1-th*th)),0.0001),exponent);
    float stripe = ceil(max(frac(uv.x*_HairOcclusionLobe.x)-0.5,0));
    // 源sample写r3.w且resource swizzle=yzwx，实际采样分量是R。
    float map = SAMPLE_TEXTURE2D(_HairOcclusionMap,sampler_HairOcclusionMap,uv*_HairOcclusionMap_ST.xy+_HairOcclusionMap_ST.zw).r;
    float region = lerp(stripe,1-map,_HairOcclusionResponse.y);
    float minimumResponse = 1-_HairOcclusionLobe.w;
    region = lerp(minimumResponse,1,region);
    region = lerp(region,1,primaryMaximum);
    float attenuation = 1+maskG*(region-1)*lobe;
    float3 attenuated = diffuse*attenuation;
    float luminance = dot(attenuated,float3(0.212673,0.715152,0.072175));
    float saturation = lerp(_HairOcclusionResponse.x,1,attenuation);
    return lerp(luminance.xxx,attenuated,saturation);
}

float3 EFEvaluateSourceCharacter(EFVaryings input, bool frontFace)
{
    EFGBufferOutput g = EFSourceCharacterGBuffer(input, frontFace, 0);
    EFSurface s = EFSampleSurface(input, frontFace);
    s.baseColor = g.target4.rgb;
    s.normalWS = EFDecodeNormal(g.target3.xy);
    // 914读取10bit GB3；此几何重画Pass不采屏幕GB，按同一UNorm精度复现接收N。
    // Eye后续程序化虹膜/角膜N只用于BRDF，不应改变阴影接收偏移。
    float3 shadowReceiverNormalWS = EFDecodeNormal(round(g.target3.xy * 1023) / 1023);
    // 源t4.g只读一次；主材质、coat和角色IBL共用同一可见性，避免外层重新引入CSM台阶。
    float characterShadow = EFCharacterShadow(input.positionWS, shadowReceiverNormalWS,
        input.positionCS.xy, (int)_CharacterShadowIndex);
    #if defined(EF_EYE)
        float2 eyeUV;
        float outsideIris;
        float2 parallaxUV = EFSourceEyeParallaxUV(input,eyeUV,outsideIris);
        float4 iris = SAMPLE_TEXTURE2D_BIAS(_BaseMap, sampler_BaseMap, parallaxUV, _SourceMipBias) * _BaseColor;
        s.baseColor = iris.rgb;
        // 源1061 PS71-74在染色之前建立间接基础色。
        float3 eyeIndirectAlbedo = iris.rgb;
        // 原虹膜Alpha/圆域的颜色乘法，不增加手调染色值。
        s.baseColor *= lerp(1, _EyeIrisTint.rgb, iris.a) * lerp(1, _EyeScleraTint.rgb, outsideIris);
        float3 corneaWS;
        EFSourceEyeNormals(input,eyeUV,outsideIris,s.normalWS,corneaWS);
        float3 corneaVS = normalize(mul((float3x3)unity_MatrixV, corneaWS));
        float4 eyeReflection = SAMPLE_TEXTURE2D_BIAS(_EyeReflectionMap, sampler_EyeReflectionMap, corneaVS.xy * 0.5 + 0.5, _SourceMipBias);
        float3 eyeReflectionColor = (eyeReflection.a * _EyeReflectionColor.rgb + eyeReflection.rgb * _EyeReflectionStrength) * (1 - outsideIris);
    #endif
    float3 ambientAlbedo = s.baseColor;
    #if defined(EF_EYE)
        ambientAlbedo = eyeIndirectAlbedo;
    #endif
    #if defined(EF_SOURCE_VIEW_TINT)
        // 原间接色LUT在视角染色之前采样；视角染色只改变直接基础色。
        ambientAlbedo = SAMPLE_TEXTURE2D_BIAS(_BaseMap, sampler_BaseMap, input.uv, _SourceMipBias).rgb * _BaseColor.rgb;
    #endif
    #if defined(EF_SOURCE_SKIN)
        // SI1_1082:359-374。GBufffer只输出简化染色，实际Forward另受区域/相机朝向控制。
        float4 skinRegion = SAMPLE_TEXTURE2D_BIAS(_SkinRegionMap,sampler_SkinRegionMap,input.uv,_SourceMipBias);
        // 源view[6]是相机朝后的Z轴：与view[0/1/2].z一致，不是look方向。
        float3 cameraBack = unity_MatrixV[2].xyz;
        float headFacing = saturate(dot(cameraBack,EFWorldTangent(_SkinForwardOS.xyz))*0.5+0.5);
        float regionWeight = lerp(headFacing,1,skinRegion.g)*skinRegion.r;
        float tintStrength = lerp(_SkinViewTintStrength.y,_SkinViewTintStrength.x,skinRegion.b)*regionWeight;
        float viewTint = saturate((1-(saturate(dot(s.normalWS,normalize(_WorldSpaceCameraPos-input.positionWS)))*0.85+0.15))*tintStrength);
        s.baseColor = ambientAlbedo*lerp(1,_ViewTintColor.rgb,viewTint);
        s.specular *= skinRegion.g;
    #endif
    #if defined(EF_SOURCE_PACKED_MASK)
        // 源t17/t18：R金属、G介质高光、B细节覆盖、A光滑；不是通用ILM约定。
        float4 sourceMask = SAMPLE_TEXTURE2D_BIAS(_SourceMaskMap, sampler_SourceMaskMap, input.uv, _SourceMipBias);
        s.metallic = sourceMask.r;
        s.specular = sourceMask.g;
        s.roughness = 1 - sourceMask.a;
    #endif
    #if defined(EF_SOURCE_PACKED_MASK) || defined(EF_EYE) || defined(EF_HAIR)
        ambientAlbedo *= _SourceIndirectAlbedoGain;
        float luminance = dot(ambientAlbedo, float3(0.212673, 0.715152, 0.072175));
        ambientAlbedo = lerp(luminance.xxx, ambientAlbedo, _SourceIndirectSaturation);
    #endif
    #if defined(EF_SOURCE_COLOR_LUT)
        ambientAlbedo = EFSourceAlbedoResponse(ambientAlbedo);
    #endif
    float3 mainDiffuse;
    float3 mainSpecularRadiance;
    float3 color = EFSourceMainLighting(s,input,ambientAlbedo,characterShadow,mainDiffuse,mainSpecularRadiance);
    #if defined(EF_EYE)
        // SI1_1061:452-468：反射在当前相机基底采样，不是固定高光图叠到屏幕上。
        color += eyeReflectionColor;
    #endif
    #if defined(EF_HAIR)
        float4 hairMask = SAMPLE_TEXTURE2D_BIAS(_HairMaskMap, sampler_HairMaskMap, input.uv, _SourceMipBias);
        float4 hairNormal = SAMPLE_TEXTURE2D_BIAS(_HairNormalMap, sampler_HairNormalMap, input.uv, _SourceMipBias) * 2 - 1;
        // 源1165 PS41-62保留插值N/T的长度，仅对重建后的法线归一化。
        // 单独归一化基底会改变发饰/发侧环等弯曲三角形上的窄高光方向。
        float3 geometricNormal = input.normalWS;
        float3 tangent = input.tangentWS.xyz;
        float3 bitangent = cross(geometricNormal, tangent) * input.tangentWS.w;
        float primaryZ = sqrt(1 - min(dot(hairNormal.xy, hairNormal.xy), 1));
        float detailZ = sqrt(1 - min(dot(hairNormal.zw, hairNormal.zw), 1));
        s.normalWS = normalize(tangent * hairNormal.x * _NormalScale + bitangent * hairNormal.y * _NormalScale + geometricNormal * primaryZ);
        s.normalWS *= frontFace ? 1 : _BackFaceNormal * 2 - 1;
        float3 detailNormal = normalize(tangent * hairNormal.z * _HairDetailNormalScale + bitangent * hairNormal.w * _HairDetailNormalScale + geometricNormal * detailZ);
        float3 objectFlow = EFWorldTangent(float3(-_HairFlowDirection, 1, 0));
        float3 flow = cross(detailNormal, objectFlow);
        flow = lerp(flow, tangent, hairMask.r);
        float3 strand = cross(detailNormal, flow) * lerp(1,input.tangentWS.w,hairMask.r);
        float3 view = normalize(_WorldSpaceCameraPos - input.positionWS);
        float3 light = SafeNormalize(_MainLightDirection.xyz);
        float3 hairRight = EFWorldTangent(_HairRightOS.xyz);
        float3 hairForward = EFWorldTangent(_HairForwardOS.xyz);
        float2 normalPlane = normalize(float2(dot(detailNormal,hairRight),dot(detailNormal,hairForward)));
        float2 viewPlane = normalize(float2(dot(view,hairRight),dot(view,hairForward)));
        float viewAlignment = pow(saturate(dot(normalPlane,viewPlane)),_HairViewAlignmentPower);
        // 源1165:1175-1196的相机/主光混合半向量；不是标准normalize(V+L)。
        float3 cameraDirection = unity_MatrixV[2].xyz;
        cameraDirection.y = light.y;
        float3 hairHalfVector = normalize(normalize(normalize(cameraDirection)*2+light)+view);
        float primaryMaximum;
        // 源1165:1268-1270用主受光/可见性组合r30，不能再直接乘Light颜色和shadow。
        color += EFSourceHairSpecular(detailNormal,strand,hairHalfVector,hairMask,viewAlignment,primaryMaximum)*mainSpecularRadiance*_SourceSpecularStrength;
        color += EFSourceHairDiffuseOcclusion(mainDiffuse,detailNormal,strand,hairHalfVector,input.uv,hairMask.g,primaryMaximum)-mainDiffuse;
    #endif
    [loop] for (int i = 0; i < min(_AdditionalLightCount, 32); i++)
    {
        float3 direction;
        float attenuation = 1;
        if (_AdditionalLightPositions[i].w == 0)
            direction = SafeNormalize(_AdditionalLightPositions[i].xyz);
        else
        {
            float3 delta = _AdditionalLightPositions[i].xyz - input.positionWS;
            float distanceSquared = dot(delta, delta);
            direction = normalize(delta);
            // 复用旧公共SourceLightEvaluation的四次距离截止与平方锥衰减。
            float cutoff = max(1 - EFSquare(distanceSquared * _AdditionalLightPositions[i].w), 0);
            float cone = saturate(dot(-direction, _AdditionalLightSpotDirections[i].xyz) * _AdditionalLightSpotAngles[i].x + _AdditionalLightSpotAngles[i].y);
            attenuation = cutoff * cutoff / max(distanceSquared, 0.0001) * cone * cone;
        }
        color += EFSourceDirect(s,input.positionWS,direction,_AdditionalLightColors[i].rgb*attenuation,
            EFAdditionalShadow(i,input.positionWS,_AdditionalLightPositions[i].xyz),input.normalWS,input.tangentWS);
    }
    #if defined(EF_SOURCE_ENVIRONMENT_REFLECTION)
        float3 environmentColor = 0;
        float3 environmentDiffuse, environmentF0;
        float environmentSpecularWeight = s.specular;
        #if defined(EF_SOURCE_ANISOTROPIC)
            environmentSpecularWeight = 1 + (_ClothAnisotropy.w - 1) * s.specular;
        #endif
        EFSourceMaterialEnergy(s.baseColor,s.metallic,environmentSpecularWeight,environmentDiffuse,environmentF0);
        float3 environmentView = normalize(_WorldSpaceCameraPos-input.positionWS);
        float3 reflectionNormal = s.normalWS;
        #if defined(EF_SOURCE_ANISOTROPIC)
            // 源1122:1298-1309。按有符号各向异性选T/B，再将视线投影至其垂面。
            float3 tangent,bitangent;
            EFSourceClothFrame(s,input.normalWS,input.tangentWS,tangent,bitangent);
            float anisotropy = s.specular*_ClothAnisotropy.x;
            float3 axis = anisotropy>0 ? bitangent : tangent;
            float3 projectedView = cross(cross(axis,environmentView),axis);
            reflectionNormal = lerp(s.normalWS,projectedView,abs(anisotropy));
            reflectionNormal *= rsqrt(max(dot(reflectionNormal,reflectionNormal),0.00006103515625));
        #endif
        environmentColor += EFSourceEnvironmentSpecularWithNormal(s.normalWS,reflectionNormal,environmentView,input.positionWS,s.roughness,environmentF0);
    #endif
    #if defined(EF_SOURCE_ANISOTROPIC)
        // 源1122:1194-1227的独立coat层，遮罩与LUT是静态材质输入。
        float coatMask = SAMPLE_TEXTURE2D_BIAS(_ClothCoatMaskMap,sampler_ClothCoatMaskMap,input.uv,_SourceMipBias).r;
        if (coatMask > 0.001)
        {
            float3 view = normalize(_WorldSpaceCameraPos - input.positionWS);
            float3 light = SafeNormalize(_MainLightDirection.xyz);
            float3 halfVector = EFSourceMainHalfVector(view,light);
            float3 coatNormal = normalize(lerp(normalize(input.normalWS),s.normalWS,_ClothCoatNormalBlend));
            float nv = saturate(dot(coatNormal,view));
            float nh = saturate(dot(coatNormal,halfVector));
            float3 lookup = SAMPLE_TEXTURE2D_LOD(_ClothCoatReflectanceMap,sampler_ClothCoatReflectanceMap,float2(nv*nv,0.5),0).rgb;
            float3 coatF0 = _ClothCoatColor.rgb * (0.04 + 0.96 * _ClothCoatMetallic) * lookup;
            float3 coatFresnel = lerp(coatF0,1,EFPow5(1-saturate(dot(view,halfVector))));
            float3 transmission = 1 - coatFresnel * coatMask;
            float coatSpecular = EFSourceSpecularLobe(1-_ClothCoatSmoothness,nh,nv);
            color = color * transmission * transmission + coatFresnel * coatMask * coatSpecular * _MainLightColor.rgb * characterShadow * _SourceSpecularStrength;
            #if defined(EF_SOURCE_ENVIRONMENT_REFLECTION)
                // 源1122:1326-1374：coat有独立法线/粗糙度和反射响应。
                environmentColor += EFSourceEnvironmentSpecular(coatNormal,view,input.positionWS,1-_ClothCoatSmoothness,coatF0) * coatMask;
            #endif
        }
    #endif
    #if defined(EF_SOURCE_ENVIRONMENT_REFLECTION)
        // 源1122:1449-1452 / 1143:1370-1373。环境sum在直接coat衰减之后加入。
        float environmentRampU = clamp(dot(s.normalWS,SafeNormalize(_MainLightDirection.xyz))+_SourceRampBias,-1,1)*0.5+0.5;
        float environmentRampVisibility = SAMPLE_TEXTURE2D_LOD(_LightingRamp,sampler_LightingRamp,float2(environmentRampU,0.5),0).a;
        float environmentVisibility = min(environmentRampVisibility,characterShadow);
        float environmentResponse = clamp(_SourceAmbientResponse,0.5,1.5)*_SourceEnvironmentStrength*lerp(_SourceIndirectStrength,1,environmentVisibility);
        color += environmentColor*environmentResponse*EFUnityAmbient(s.normalWS)*_SourceAmbientTint.rgb;
    #endif
    #if defined(EF_SOURCE_PARALLAX_GLOW)
        color += EFSourceParallaxGlow(input,s,frontFace);
    #endif
    return max(color + s.emission, 0);
}
#endif
