Shader "Endfield/SourceBackground"
{
    Properties
    {
        _BaseMap("台面底图",2D)="white"{}
        _PatternMap("台面距离场格网",2D)="white"{}
        _BaseColor("台面底色",Color)=(0.7911512,0.7911512,0.7911512,1)
        _PatternColor("格网颜色与混合强度",Vector)=(1,1,1,0.04313726)
        _PatternUV_ST("格网UV缩放与偏移",Vector)=(1,1,0.72,0.45)
        _BaseUV_ST("底图UV缩放与偏移",Vector)=(1,1,0,0)
        _DistanceFade("距离场近远边界",Vector)=(30.7,14.1,0,0)
        _BaseGain("底图增益",Float)=1
        _BaseCoverage("底图覆盖率",Float)=1
        _SourceMipBias("源采样Mip偏移",Float)=0
        [Toggle] _ReceiveShadows("接收实时主光阴影",Float)=1
        [Enum(UnityEngine.Rendering.CullMode)] _Cull("剔除",Float)=2
    }
    SubShader
    {
        Tags { "RenderPipeline"="EndfieldPipeline" "Queue"="Transparent-100" "RenderType"="Opaque" }
        Pass
        {
            Name "BackgroundSurface"
            Tags { "LightMode"="EndfieldForward" }
            Cull [_Cull] ZWrite On ZTest LEqual Blend One Zero
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Frag
            #include "Library/Coordinates.hlsl"
            #include "Library/Shadows.hlsl"
            Texture2D<float4> _BaseMap, _PatternMap;
            SamplerState sampler_Background_linear_repeat;
            CBUFFER_START(UnityPerMaterial)
            float4 _BaseColor, _PatternColor, _PatternUV_ST, _BaseUV_ST, _DistanceFade;
            float _BaseGain, _BaseCoverage, _SourceMipBias, _Cull, _ReceiveShadows;
            CBUFFER_END
            float4 _MainLightDirection, _MainLightColor;
            struct Attributes { float3 position:POSITION; float3 normal:NORMAL; float2 uv:TEXCOORD0; };
            struct Varyings { float4 position:SV_POSITION; float2 uv:TEXCOORD0; float3 world:TEXCOORD1; float3 normal:TEXCOORD2; };
            Varyings Vert(Attributes i)
            {
                Varyings o;
                o.world=EFWorldPosition(i.position);
                o.position=mul(unity_MatrixVP,float4(o.world,1));
                o.normal=EFWorldNormal(i.normal);
                o.uv=i.uv;
                return o;
            }
            float4 Frag(Varyings i):SV_Target
            {
                // 源1210：底图RGBA乘底色；格网R为距离场、A参与覆盖率。
                float4 baseSample=_BaseMap.SampleBias(sampler_Background_linear_repeat,i.uv*_BaseUV_ST.xy+_BaseUV_ST.zw,_SourceMipBias)*_BaseColor;
                float4 pattern=_PatternMap.SampleBias(sampler_Background_linear_repeat,i.uv*_PatternUV_ST.xy+_PatternUV_ST.zw,_SourceMipBias);
                float distanceValue=0.5-pattern.r;
                float gradientLength=length(float2(ddx_coarse(distanceValue),ddy_coarse(distanceValue)));
                float antiAliasedDistance=distanceValue/gradientLength;
                // 源673/1210用重建位置计算view depth；此处直接使用当前Unity相机的世界位置。
                float viewDepth=abs(mul(unity_MatrixV,float4(i.world,1)).z);
                float fade=saturate((viewDepth-_DistanceFade.x)/(_DistanceFade.y-_DistanceFade.x));
                float coverage=saturate(0.5-lerp(distanceValue,antiAliasedDistance,fade));
                float layerCoverage=saturate((baseSample.a*_BaseCoverage+pattern.a)*_PatternColor.a);
                float3 color=baseSample.rgb*_BaseGain+coverage*_PatternColor.rgb*layerCoverage*pattern.a;
                // 本帧1210雾体积开关=0，两个高度雾密度=0、透射率下限=1，源最终分支退化为此颜色。
                // 台面是实际几何，阴影必须用其世界位置查询当前Unity主光，而不是用屏幕UV伪造贴片。
                // 源1210的底图/格网为无光照合成；此接收器是可编辑的实时场景能力，强度与过滤由灯光控制。
                float3 normal=SafeNormalize(i.normal);
                float3 ambient=max(EFUnityAmbient(normal),0);
                float3 main=max(_MainLightColor.rgb,0)*saturate(dot(normal,SafeNormalize(_MainLightDirection.xyz)));
                float3 total=ambient+main;
                // 原底图已含环境外观，只按当前直接/间接能量占比衰减；阴影不消灭环境照明。
                float3 ratio=(ambient+main*EFMainShadow(i.world))/max(total,1e-6);
                float3 multiplier=lerp(1,ratio,step(1e-6,total));
                multiplier=lerp(1,multiplier,saturate(_ReceiveShadows));
                return float4(color*multiplier,baseSample.a*_BaseCoverage);
            }
            ENDHLSL
        }
    }
}
