#ifndef ENDFIELD_LIGHTING_INCLUDED
#define ENDFIELD_LIGHTING_INCLUDED
#include "BRDF.hlsl"
#include "Shadows.hlsl"
float4 _MainLightDirection;
float4 _MainLightColor;
int _AdditionalLightCount;
float4 _AdditionalLightPositions[32];
float4 _AdditionalLightColors[32];
float4 _AdditionalLightSpotDirections[32];
float4 _AdditionalLightSpotAngles[32];
float4 _AmbientSkyColor;
float4 _AmbientGroundColor;
float4 _AmbientSHAr, _AmbientSHAg, _AmbientSHAb;
float4 _AmbientSHBr, _AmbientSHBg, _AmbientSHBb, _AmbientSHC;

float3 EFEvaluateLighting(EFSurface s, float3 positionWS)
{
    float3 view = SafeNormalize(_WorldSpaceCameraPos - positionWS);
    float3 color = s.emission;
    #if defined(EF_FULLSCREEN_LIGHTING)
        // 全屏没有逐Renderer绑定，C#以原生SHCoefficients上传当前ambientProbe同一组系数。
        float4 normal = float4(s.normalWS, 1);
        float4 quadratic = s.normalWS.xyzz * s.normalWS.yzzx;
        float3 ambient = float3(dot(_AmbientSHAr,normal),dot(_AmbientSHAg,normal),dot(_AmbientSHAb,normal));
        ambient += float3(dot(_AmbientSHBr,quadratic),dot(_AmbientSHBg,quadratic),dot(_AmbientSHBb,quadratic));
        ambient += _AmbientSHC.rgb * (s.normalWS.x * s.normalWS.x - s.normalWS.y * s.normalWS.y);
        ambient = max(ambient, 0);
    #else
        float3 ambient = EFUnityAmbient(s.normalWS);
    #endif
    color += ambient * s.baseColor * s.occlusion * (1 - s.metallic);
    color += EFEvaluateBRDF(s, view, SafeNormalize(_MainLightDirection.xyz), _MainLightColor.rgb, EFMainShadow(positionWS));
    [loop] for (int i = 0; i < min(_AdditionalLightCount, 32); i++)
    {
        float3 direction;
        float attenuation = 1;
        if (_AdditionalLightPositions[i].w == 0)
            direction = SafeNormalize(_AdditionalLightPositions[i].xyz);
        else
        {
            float3 delta = _AdditionalLightPositions[i].xyz - positionWS;
            float distanceSquared = max(dot(delta, delta), 1e-4);
            direction = delta * rsqrt(distanceSquared);
            float range = saturate(1 - EFSquare(distanceSquared * _AdditionalLightPositions[i].w));
            attenuation = range * range / distanceSquared;
            float cone = saturate(dot(-direction, _AdditionalLightSpotDirections[i].xyz) * _AdditionalLightSpotAngles[i].x + _AdditionalLightSpotAngles[i].y);
            attenuation *= cone * cone;
        }
        color += EFEvaluateBRDF(s, view, direction, _AdditionalLightColors[i].rgb * attenuation,
            EFAdditionalShadow(i, positionWS, _AdditionalLightPositions[i].xyz));
    }
    return max(color, 0);
}
#endif
