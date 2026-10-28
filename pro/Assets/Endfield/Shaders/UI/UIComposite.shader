Shader "Hidden/Endfield/UI/Composite"
{
    SubShader
    {
        Tags { "RenderPipeline"="EndfieldPipeline" }
        Cull Off ZWrite Off ZTest Always
        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.core/ShaderLibrary/Common.hlsl"
        #include "Packages/com.unity.render-pipelines.core/ShaderLibrary/Color.hlsl"
        Texture2D<float4> _EndfieldUIResolvedSceneTexture;
        Texture2D<float4> _EndfieldUICompositionTexture;
        SamplerState sampler_UI_linear_clamp;
        float4 _EndfieldOutputScaleBias;
        struct Varyings { float4 position:SV_POSITION; float2 uv:TEXCOORD0; };
        Varyings Vert(uint id:SV_VertexID)
        {
            Varyings o;
            o.position=GetFullScreenTriangleVertexPosition(id);
            o.uv=GetFullScreenTriangleTexCoord(id);
            return o;
        }
        float4 Initialize(Varyings i):SV_Target
        {
            float4 color=_EndfieldUIResolvedSceneTexture.SampleLevel(sampler_UI_linear_clamp,i.uv,0);
            return float4(LinearToSRGB(color.rgb),color.a);
        }
        float4 Resolve(Varyings i):SV_Target
        {
            float2 uv=i.uv*_EndfieldOutputScaleBias.xy+_EndfieldOutputScaleBias.zw;
            float4 color=_EndfieldUICompositionTexture.SampleLevel(sampler_UI_linear_clamp,uv,0);
            return float4(SRGBToLinear(color.rgb),color.a);
        }
        ENDHLSL
        Pass
        {
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Initialize
            ENDHLSL
        }
        Pass
        {
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vert
            #pragma fragment Resolve
            ENDHLSL
        }
    }
}
