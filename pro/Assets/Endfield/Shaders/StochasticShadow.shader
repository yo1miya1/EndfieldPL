Shader "Endfield/StochasticShadow"
{
    Properties
    {
        _AlphaMap("源覆盖率贴图Alpha",2D)="white"{}
        _Opacity("覆盖率增益",Float)=1
        _SourceMipBias("源Mip偏移",Float)=0
        [Enum(UnityEngine.Rendering.CullMode)] _Cull("剔除",Float)=0
    }
    SubShader
    {
        Tags { "RenderPipeline"="EndfieldPipeline" "RenderType"="TransparentCutout" "Queue"="Geometry" }
        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode"="ShadowCaster" }
            Cull [_Cull] ZWrite On ZTest LEqual ColorMask 0
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vertex
            #pragma fragment Fragment
            #include "Library/Coordinates.hlsl"
            TEXTURE2D(_AlphaMap); SAMPLER(sampler_AlphaMap);
            CBUFFER_START(UnityPerMaterial)
            float _Opacity, _SourceMipBias, _Cull;
            CBUFFER_END
            float4 _ShadowBias, _ShadowLightDirection, _ShadowLightPosition;
            float _ShadowLightType;
            struct Attributes {float3 position:POSITION;float3 normal:NORMAL;float2 uv:TEXCOORD0;};
            struct Varyings {float4 position:SV_POSITION;float2 uv:TEXCOORD0;};
            Varyings Vertex(Attributes i)
            {
                Varyings o;
                float3 world=EFWorldPosition(i.position);
                float3 normal=EFWorldNormal(i.normal);
                // 方向光共用常量方向；点光和聚光按每个顶点到光源的位置计算，不能沿用主方向光偏移。
                float3 towardLight=_ShadowLightType>.5 ? normalize(_ShadowLightPosition.xyz-world) : _ShadowLightDirection.xyz;
                float normalBias=_ShadowBias.y*(1-saturate(dot(normal,towardLight)));
                world+=normal*normalBias+towardLight*_ShadowBias.x;
                o.position=mul(unity_MatrixVP,float4(world,1));
                #if UNITY_REVERSED_Z
                    o.position.z=min(o.position.z,o.position.w*UNITY_NEAR_CLIP_VALUE);
                #else
                    o.position.z=max(o.position.z,o.position.w*UNITY_NEAR_CLIP_VALUE);
                #endif
                o.uv=i.uv;
                return o;
            }
            float4 Fragment(Varyings i):SV_Target
            {
                // 源424 PS：sqrt(alpha*cb1[6].w)与阴影图像素坐标噪声比较。
                // 两次frac、原常数和负值分支顺序均保留；没有固定0.5裁剪替代。
                float coverage=sqrt(SAMPLE_TEXTURE2D_BIAS(_AlphaMap,sampler_AlphaMap,i.uv,_SourceMipBias).a*_Opacity);
                float noise=frac(dot(i.position.xy,float2(0.06711056,0.00583715)));
                noise=frac(noise*52.9829189);
                noise=coverage>=0 ? noise : -noise;
                clip(coverage-noise);
                return 0;
            }
            ENDHLSL
        }
        Pass
        {
            Name "CharacterShadowCaster"
            Tags { "LightMode"="CharacterShadowCaster" }
            Cull [_Cull] ZWrite On ZTest LEqual ColorMask 0
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex CharacterVertex
            #pragma fragment CharacterFragment
            #include "Library/Coordinates.hlsl"
            TEXTURE2D(_AlphaMap); SAMPLER(sampler_AlphaMap);
            CBUFFER_START(UnityPerMaterial)
            float _Opacity, _SourceMipBias, _Cull;
            CBUFFER_END
            // 独立角色图遵循源位置路径：不读N，也不把0 bias乘NaN法线后加回位置。
            struct Attributes {float3 position:POSITION;float2 uv:TEXCOORD0;};
            struct Varyings {float4 position:SV_POSITION;float2 uv:TEXCOORD0;};
            Varyings CharacterVertex(Attributes i)
            {
                Varyings o;
                float3 world=EFWorldPosition(i.position);
                o.position=mul(unity_MatrixVP,float4(world,1));
                #if UNITY_REVERSED_Z
                    o.position.z=min(o.position.z,o.position.w*UNITY_NEAR_CLIP_VALUE);
                #else
                    o.position.z=max(o.position.z,o.position.w*UNITY_NEAR_CLIP_VALUE);
                #endif
                o.uv=i.uv;
                return o;
            }
            float4 CharacterFragment(Varyings i):SV_Target
            {
                // coverage保持源424；仅caster顶点位置与普通Unity CSM的偏移路径分开。
                float coverage=sqrt(SAMPLE_TEXTURE2D_BIAS(_AlphaMap,sampler_AlphaMap,i.uv,_SourceMipBias).a*_Opacity);
                float noise=frac(dot(i.position.xy,float2(0.06711056,0.00583715)));
                noise=frac(noise*52.9829189);
                noise=coverage>=0 ? noise : -noise;
                clip(coverage-noise);
                return 0;
            }
            ENDHLSL
        }
    }
}
