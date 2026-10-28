Shader "Hidden/Endfield/ColorLut"
{
    SubShader
    {
        Tags { "RenderPipeline"="EndfieldPipeline" }
        Pass
        {
            Name "GenerateColorLut"
            Cull Off ZWrite Off ZTest Always
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex EFFullscreenVertex
            #pragma fragment Fragment
            #include "Library/SourceColorLut.hlsl"
            float4 Fragment(EFFullscreenVaryings input) : SV_Target
            {
                float4 color;
                EFLutPS(input.positionCS, input.uv, color);
                return color;
            }
            ENDHLSL
        }
    }
}
