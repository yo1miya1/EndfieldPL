Shader "Hidden/Endfield/DeferredLighting"
{
    SubShader
    {
        Tags { "RenderPipeline"="EndfieldPipeline" }
        Pass
        {
            Name "DeferredLighting"
            Cull Off ZWrite Off ZTest Always
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex EFFullscreenVertex
            #pragma fragment Fragment
            #define EF_FULLSCREEN_LIGHTING 1
            #include "Library/Lighting.hlsl"
            TEXTURE2D(_GBuffer0); TEXTURE2D(_GBuffer1); TEXTURE2D(_GBuffer2);
            TEXTURE2D(_GBuffer3); TEXTURE2D(_GBuffer4); TEXTURE2D(_CameraDepthTexture);
            SAMPLER(sampler_PointClamp);
            float4 _CameraBackgroundColor;
            float4 Fragment(EFFullscreenVaryings input) : SV_Target
            {
                float depth = SAMPLE_TEXTURE2D_LOD(_CameraDepthTexture, sampler_PointClamp, input.uv, 0).r;
                #if UNITY_REVERSED_Z
                    if (depth <= 0.0000001) return _CameraBackgroundColor;
                #else
                    if (depth >= 0.9999999) return _CameraBackgroundColor;
                    depth = lerp(UNITY_NEAR_CLIP_VALUE, 1, depth);
                #endif
                EFSurface s = EFDecodeGBuffer(
                    SAMPLE_TEXTURE2D_LOD(_GBuffer0, sampler_PointClamp, input.uv, 0),
                    SAMPLE_TEXTURE2D_LOD(_GBuffer1, sampler_PointClamp, input.uv, 0),
                    SAMPLE_TEXTURE2D_LOD(_GBuffer2, sampler_PointClamp, input.uv, 0),
                    SAMPLE_TEXTURE2D_LOD(_GBuffer3, sampler_PointClamp, input.uv, 0),
                    SAMPLE_TEXTURE2D_LOD(_GBuffer4, sampler_PointClamp, input.uv, 0));
                return float4(EFEvaluateLighting(s, EFReconstructWorld(input.uv, depth)), 1);
            }
            ENDHLSL
        }
    }
}
