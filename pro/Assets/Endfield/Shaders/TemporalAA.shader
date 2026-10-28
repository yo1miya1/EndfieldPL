Shader "Hidden/Endfield/TemporalAA"
{
    SubShader
    {
        Tags { "RenderPipeline"="EndfieldPipeline" }
        Cull Off ZWrite Off ZTest Always
        HLSLINCLUDE
        #pragma target 4.5
        #include "Library/Coordinates.hlsl"
        #include "Packages/com.unity.render-pipelines.core/ShaderLibrary/Color.hlsl"
        TEXTURE2D(_SourceTexture);
        TEXTURE2D(_TemporalHistoryTexture);
        TEXTURE2D(_TemporalMotionTexture);
        TEXTURE2D(_CameraDepthTexture);
        SAMPLER(sampler_LinearClamp);
        SAMPLER(sampler_PointClamp);
        float4 _SourceTexture_TexelSize;
        float _TemporalHistoryValid, _TemporalCurrentWeight, _TemporalVarianceScale;

        float2 ClipToUV(float4 clip)
        {
            float2 uv = clip.xy / clip.w * .5 + .5;
            #if UNITY_UV_STARTS_AT_TOP
                uv.y = 1 - uv.y;
            #endif
            return uv;
        }
        float4 CameraMotion(EFFullscreenVaryings input) : SV_Target
        {
            float depth = SAMPLE_TEXTURE2D_LOD(_CameraDepthTexture, sampler_PointClamp, input.uv, 0).r;
            float4 world = float4(EFReconstructWorld(input.uv, depth), 1);
            float4 current = mul(_EndfieldNonJitteredViewProjection, world);
            float4 previous = mul(_TemporalPreviousViewProjection, world);
            return float4(ClipToUV(previous) - ClipToUV(current), 0, 1);
        }
        half3 ToWorking(half3 rgb) { return RGBToYCoCg(rgb); }
        half3 FromWorking(half3 ycocg) { return max(YCoCgToRGB(ycocg), 0); }
        half3 Current(float2 uv) { return ToWorking(SAMPLE_TEXTURE2D_LOD(_SourceTexture, sampler_PointClamp, uv, 0).rgb); }
        half3 History(float2 uv) { return ToWorking(SAMPLE_TEXTURE2D_LOD(_TemporalHistoryTexture, sampler_LinearClamp, uv, 0).rgb); }

        // Unity URP TemporalAA High的Catmull-Rom五次双线性采样，保留原系数及归一化。
        half3 BicubicHistory(float2 uv)
        {
            float2 samplePosition = uv * _SourceTexture_TexelSize.zw;
            float2 center = floor(samplePosition - .5) + .5;
            half2 f = samplePosition - center;
            half2 f2 = f * f, f3 = f2 * f;
            half2 w0 = -.5 * f3 + f2 - .5 * f;
            half2 w1 = 1.5 * f3 - 2.5 * f2 + 1;
            half2 w2 = -1.5 * f3 + 2 * f2 + .5 * f;
            half2 w3 = .5 * f3 - .5 * f2;
            half2 w12 = w1 + w2;
            float2 uv0 = _SourceTexture_TexelSize.xy * (center - 1);
            float2 uv3 = _SourceTexture_TexelSize.xy * (center + 2);
            float2 uv12 = _SourceTexture_TexelSize.xy * (center + w2 / w12);
            half a = w12.x * w0.y, b = w0.x * w12.y, c = w12.x * w12.y;
            half d = w3.x * w12.y, e = w12.x * w3.y;
            return (History(float2(uv12.x, uv0.y)) * a + History(float2(uv0.x, uv12.y)) * b
                + History(uv12) * c + History(float2(uv3.x, uv12.y)) * d
                + History(float2(uv12.x, uv3.y)) * e) / (a + b + c + d + e);
        }
        float4 Resolve(EFFullscreenVaryings input) : SV_Target
        {
            float2 uv = input.uv;
            half3 center = Current(uv);
            if (_TemporalHistoryValid == 0) return float4(FromWorking(center), 1);

            half3 minimum = center, maximum = center, moment1 = 0, moment2 = 0;
            float bestDepth = SAMPLE_TEXTURE2D_LOD(_CameraDepthTexture, sampler_PointClamp, uv, 0).r;
            #if UNITY_REVERSED_Z
                bestDepth = 1 - bestDepth;
            #endif
            float2 bestUV = uv;
            // URP High：3x3颜色方差约束，同时用最近深度扩张运动矢量，保护轮廓。
            [unroll] for (int y = -1; y <= 1; y++)
            [unroll] for (int x = -1; x <= 1; x++)
            {
                float2 neighborUV = uv + float2(x, y) * _SourceTexture_TexelSize.xy;
                half3 color = Current(neighborUV);
                minimum = min(minimum, color); maximum = max(maximum, color);
                moment1 += color; moment2 += color * color;
                float depth = SAMPLE_TEXTURE2D_LOD(_CameraDepthTexture, sampler_PointClamp, neighborUV, 0).r;
                #if UNITY_REVERSED_Z
                    depth = 1 - depth;
                #endif
                if (depth < bestDepth) { bestDepth = depth; bestUV = neighborUV; }
            }
            half3 mean = moment1 / 9;
            half3 deviation = sqrt(abs(moment2 / 9 - mean * mean));
            minimum = max(minimum, mean - _TemporalVarianceScale * deviation);
            maximum = min(maximum, mean + _TemporalVarianceScale * deviation);
            float2 motion = SAMPLE_TEXTURE2D_LOD(_TemporalMotionTexture, sampler_PointClamp, bestUV, 0).xy;
            float2 historyUV = uv + motion;
            half3 accumulated = clamp(BicubicHistory(historyUV), minimum, maximum);
            half influence = any(abs(historyUV - .5) > .5) ? 1 : _TemporalCurrentWeight;
            // URP的感知亮度加权，避免HDR高亮在颜色插值时过度支配历史。
            half3 perceptualHistory = accumulated / (accumulated.x + 1);
            half3 perceptualCenter = center / (center.x + 1);
            half3 perceptual = lerp(perceptualHistory, perceptualCenter, influence);
            return float4(FromWorking(perceptual / max(1 - perceptual.x, .0001)), 1);
        }
        ENDHLSL
        Pass
        {
            Name "TemporalResolve"
            HLSLPROGRAM
            #pragma vertex EFFullscreenVertex
            #pragma fragment Resolve
            ENDHLSL
        }
        Pass
        {
            Name "CameraMotion"
            HLSLPROGRAM
            #pragma vertex EFFullscreenVertex
            #pragma fragment CameraMotion
            ENDHLSL
        }
    }
}
