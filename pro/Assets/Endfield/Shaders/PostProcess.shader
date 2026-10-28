Shader "Hidden/Endfield/PostProcess"
{
    SubShader
    {
        Tags { "RenderPipeline"="EndfieldPipeline" }
        Cull Off ZWrite Off ZTest Always
        HLSLINCLUDE
        #pragma target 4.5
        #include "Library/Coordinates.hlsl"
        #include "Library/GBuffer.hlsl"
        #include "Library/Shadows.hlsl"
        #include "Library/CharacterShadows.hlsl"
        #include "Packages/com.unity.render-pipelines.core/ShaderLibrary/Filtering.hlsl"
        TEXTURE2D(_SourceTexture); SAMPLER(sampler_LinearClamp);
        TEXTURE2D(_BloomTexture);
        TEXTURE2D(_BloomLowTexture);
        TEXTURE2D(_ColorLutTexture);
        TEXTURE2D(_GBuffer0); TEXTURE2D(_GBuffer1); TEXTURE2D(_GBuffer2);
        TEXTURE2D(_GBuffer3); TEXTURE2D(_GBuffer4); TEXTURE2D(_CameraDepthTexture);
        SAMPLER(sampler_PointClamp);
        float4 _SourceScaleBias;
        float4 _SourceTexture_TexelSize;
        float4 _BloomBlurDirection;
        float _PostExposure, _PostContrast, _PostSaturation, _PostToneMapping, _PostVignette;
        float _BloomIntensity, _BloomThreshold;
        int _DebugView;
        float4 _DofNearParams, _DofFarParams;
        float4 _BloomThresholdParams, _BloomTint, _BloomLowTexture_TexelSize;
        float _BloomScatter;
        float _UIBlurHighlightClamp;
        float4 _ColorLutParams;
        float _SourceBloomHighlightSuppression;
        float4 _SourceVignetteCenter, _SourceVignetteShape, _SourceVignetteColor;
        float2 EFSourceUV(float2 uv) { return uv * _SourceScaleBias.xy + _SourceScaleBias.zw; }
        float3 EFSource(float2 uv) { return SAMPLE_TEXTURE2D_LOD(_SourceTexture, sampler_LinearClamp, uv, 0).rgb; }
        float4 FinalFragment(EFFullscreenVaryings input) : SV_Target
        {
            float2 uv = EFSourceUV(input.uv);
            float3 color = EFSource(uv) + SAMPLE_TEXTURE2D_LOD(_BloomTexture, sampler_LinearClamp, uv, 0).rgb * _BloomIntensity;
            color *= _PostExposure;
            // ACES拟合是可编辑显示基线；不是源LUT/曝光管线的等价替代。
            if (_PostToneMapping > 0.5) color = saturate((color * (2.51 * color + 0.03)) / (color * (2.43 * color + 0.59) + 0.14));
            color = (color - 0.18) * _PostContrast + 0.18;
            float luminance = dot(color, float3(0.2126, 0.7152, 0.0722));
            color = lerp(luminance.xxx, color, _PostSaturation);
            float2 radial = input.uv * 2 - 1;
            color *= 1 - _PostVignette * saturate(dot(radial, radial) * 0.5);
            return float4(max(color, 0), 1);
        }
        float4 PrefilterFragment(EFFullscreenVaryings input) : SV_Target
        {
            float3 color = EFSource(EFSourceUV(input.uv));
            float brightness = max(color.r, max(color.g, color.b));
            return float4(color * max(brightness - _BloomThreshold, 0) / max(brightness, 0.0001), 1);
        }
        float4 BlurFragment(EFFullscreenVaryings input) : SV_Target
        {
            float2 uv = EFSourceUV(input.uv);
            float2 delta = _BloomBlurDirection.xy * _SourceTexture_TexelSize.xy;
            float3 color = EFSource(uv) * 0.227027;
            color += (EFSource(uv + delta * 1.384615) + EFSource(uv - delta * 1.384615)) * 0.316216;
            color += (EFSource(uv + delta * 3.230769) + EFSource(uv - delta * 3.230769)) * 0.070270;
            return float4(color, 1);
        }
        float4 DebugFragment(EFFullscreenVaryings input) : SV_Target
        {
            float2 uv = EFSourceUV(input.uv);
            float4 g0 = SAMPLE_TEXTURE2D_LOD(_GBuffer0, sampler_PointClamp, uv, 0);
            float4 g1 = SAMPLE_TEXTURE2D_LOD(_GBuffer1, sampler_PointClamp, uv, 0);
            float4 g2 = SAMPLE_TEXTURE2D_LOD(_GBuffer2, sampler_PointClamp, uv, 0);
            float4 g3 = SAMPLE_TEXTURE2D_LOD(_GBuffer3, sampler_PointClamp, uv, 0);
            float4 g4 = SAMPLE_TEXTURE2D_LOD(_GBuffer4, sampler_PointClamp, uv, 0);
            float depth = SAMPLE_TEXTURE2D_LOD(_CameraDepthTexture, sampler_PointClamp, uv, 0).r;
            #if UNITY_REVERSED_Z
                bool isBackground = depth <= 0.0000001;
            #else
                bool isBackground = depth >= 0.9999999;
            #endif
            if (isBackground && _DebugView == 8) return 1;
            if (isBackground && _DebugView == 4) return float4(0, 0, 0, 1);
            float3 color = EFSource(uv);
            if (_DebugView == 1) color = g0.rgb;
            if (_DebugView == 2) color = float3(EFDecodeMotion(g1.xy) * 10 + 0.5, 0.5);
            if (_DebugView == 3) color = g2.xyz;
            if (_DebugView == 4) color = EFDecodeNormal(g3.xy) * 0.5 + 0.5;
            if (_DebugView == 5) color = g3.zzz;
            if (_DebugView == 6) color = g4.rgb;
            if (_DebugView == 7) color = depth.xxx;
            if (_DebugView == 8)
            {
                // G1.w在A2附件中由.4量化到1/3；普通PBR/环境不使用角色one-hot。
                bool character = g1.z > .99 && abs(g1.w - (1.0 / 3.0)) < .05;
                int characterIndex = character ? EFCharacterShadowIndexFromPayload(g2) : -1;
                color = EFCharacterShadow(EFReconstructWorld(uv, depth), EFDecodeNormal(g3.xy), input.positionCS.xy, characterIndex).xxx;
            }
            if (_DebugView == 9) color = SAMPLE_TEXTURE2D_LOD(_MainLightShadowmapTexture, sampler_PointClamp, uv, 0).rrr;
            return float4(color, 1);
        }
        // SI1_1742 源CoC；原区间相等或半径零分支输出零，far有值优先far。
        float EFSourceCoC(float depth)
        {
            float nearCoC = 0, farCoC = 0;
            if (_DofNearParams.x != _DofNearParams.y && _DofNearParams.z != 0)
                nearCoC = -saturate((depth - _DofNearParams.y) / (_DofNearParams.x - _DofNearParams.y));
            if (_DofFarParams.x != _DofFarParams.y && _DofFarParams.z != 0)
                farCoC = saturate((depth - _DofFarParams.x) / (_DofFarParams.y - _DofFarParams.x));
            return farCoC > 0 ? farCoC : nearCoC;
        }
        float4 DofFragment(EFFullscreenVaryings input) : SV_Target
        {
            float2 uv = EFSourceUV(input.uv);
            float deviceDepth = SAMPLE_TEXTURE2D_LOD(_CameraDepthTexture, sampler_PointClamp, uv, 0).r;
            float depth = LinearEyeDepth(deviceDepth, _ZBufferParams);
            float coc = EFSourceCoC(depth);
            float radius = abs(coc) * (coc < 0 ? _DofNearParams.z : _DofFarParams.z);
            float2 texel = _SourceTexture_TexelSize.xy * radius;
            float3 color = EFSource(uv) * 4;
            float weight = 4;
            // 分离层/时间重投影未接入时使用单帧13点合成；区间和半径仍按源值。
            [unroll] for (int i = 0; i < 12; i++)
            {
                float angle = (i + 0.5) * (TWO_PI / 12);
                float2 delta = float2(cos(angle), sin(angle)) * texel;
                color += EFSource(uv + delta);
                weight += 1;
            }
            return float4(color / weight, 1);
        }
        float3 EFSourceBloomThreshold(float3 color)
        {
            float brightness = max(color.r, max(color.g, color.b));
            float soft = clamp(brightness - _BloomThresholdParams.y, 0, _BloomThresholdParams.z);
            soft = soft * soft * _BloomThresholdParams.w;
            float weight = max(brightness - _BloomThresholdParams.x, soft) / max(brightness, 0.0001);
            return color * weight;
        }
        float4 SourceBloomPrefilter(EFFullscreenVaryings input) : SV_Target
        {
            float2 uv = EFSourceUV(input.uv);
            // SI1_1960 的13点抗闪烁核和亮度加权；保留源最后一个重复偏移。
            const float2 offsets[13] = {
                float2(0,0),float2(-2,-2),float2(2,-2),float2(2,2),float2(-2,2),
                float2(-2,0),float2(2,0),float2(0,2),float2(0,-2),
                float2(-1,1),float2(1,1),float2(-1,-1),float2(-1,1) };
            const float weights[13] = {4,1,1,1,1,2,2,2,2,4,4,4,4};
            float3 sum = 0;
            float sumWeights = 0;
            [unroll] for (int i = 0; i < 13; i++)
            {
                float3 color = EFSourceBloomThreshold(EFSource(uv + offsets[i] * _SourceTexture_TexelSize.xy)) * _PostExposure;
                float weight = weights[i] / (dot(color, float3(0.212673,0.715152,0.072175)) + 1);
                sum += color * weight;
                sumWeights += weight;
            }
            return float4(sum / sumWeights, 1);
        }
        float4 SourceBloomDownsample(EFFullscreenVaryings input) : SV_Target
        {
            float2 uv = EFSourceUV(input.uv);
            // SI1_1969 的9项二项核，合并相邻双线性采样为5项；半字共享内存改为float采样。
            const float offsets[5] = {0,-1.3333333333,1.3333333333,-3.1111111111,3.1111111111};
            const float weights[5] = {70.0/256,84.0/256,84.0/256,9.0/256,9.0/256};
            float3 color = 0;
            [unroll] for (int y = 0; y < 5; y++)
                [unroll] for (int x = 0; x < 5; x++)
                    color += EFSource(uv + float2(offsets[x], offsets[y]) * _SourceTexture_TexelSize.xy) * weights[x] * weights[y];
            return float4(color, 1);
        }
        float4 SourceBloomUpsample(EFFullscreenVaryings input) : SV_Target
        {
            float2 uv = EFSourceUV(input.uv);
            float4 size = _BloomLowTexture_TexelSize.zwxy;
            float3 low = SampleTexture2DBicubic(TEXTURE2D_ARGS(_BloomLowTexture, sampler_LinearClamp), uv, size, 1 - size.zw, 0).rgb;
            // SI1_2041 的source + scatter*(bicubicLow-source)。
            return float4(lerp(EFSource(uv), low, _BloomScatter), 1);
        }
        float3 EFSourceDisplayLut(float3 color)
        {
            // 原LogC参数按IEEE常量恢复，禁止把线性RGB直接saturate输入LUT。
            float3 logColor = saturate(log2(max(color * 5.555555820465088 + 0.04799623787403107, 0)) * 0.07349978387355804 + 0.3860360085964203);
            float3 grid = logColor.brg * _ColorLutParams.z;
            float slice = floor(grid.x);
            float2 uv = float2(grid.y * _ColorLutParams.x + 0.5 * _ColorLutParams.x + slice * _ColorLutParams.y,
                               grid.z * _ColorLutParams.y + 0.5 * _ColorLutParams.y);
            float3 a = SAMPLE_TEXTURE2D_LOD(_ColorLutTexture, sampler_LinearClamp, uv, 0).rgb;
            float3 b = SAMPLE_TEXTURE2D_LOD(_ColorLutTexture, sampler_LinearClamp, uv + float2(_ColorLutParams.y, 0), 0).rgb;
            return lerp(a, b, grid.x - slice);
        }
        float3 EFSourceDisplayVignette(float2 uv)
        {
            float intensity = _SourceVignetteCenter.w;
            float4 shape = _SourceVignetteShape;
            float2 p = abs(uv - _SourceVignetteCenter.xy) * lerp(shape.x, 1, intensity);
            float xScale = lerp(1, saturate(1.05 * shape.x) * 1.5 - 1, intensity);
            float yScale = lerp(1, shape.x * 2 - 1, intensity);
            float aspect = _ScreenParams.x / _ScreenParams.y;
            float aspectScale = lerp(1, aspect, shape.w);
            aspectScale = lerp(aspectScale, 0.5625 * aspect, intensity);
            p = saturate(float2(p.x * xScale * aspectScale, p.y * yScale + saturate(shape.x - 2.8) * 5));
            p = pow(p, shape.z);
            float vignette = pow(max(1 - dot(p, p), 0), shape.y);
            return lerp(_SourceVignetteColor.rgb, 1, vignette);
        }
        float4 SourceDisplayFragment(EFFullscreenVaryings input) : SV_Target
        {
            float2 uv = EFSourceUV(input.uv);
            float3 source = EFSource(uv);
            float3 exposed = source * _PostExposure;
            float3 bloom = SAMPLE_TEXTURE2D_LOD(_BloomTexture, sampler_LinearClamp, uv, 0).rgb;
            float3 adjustedBloom = 1.493799924850464 * pow(bloom, 0.33) - 0.7;
            bloom = float3(bloom.r * (1 - _SourceBloomHighlightSuppression) > 0.3 ? adjustedBloom.r : bloom.r,
                           bloom.g * (1 - _SourceBloomHighlightSuppression) > 0.3 ? adjustedBloom.g : bloom.g,
                           bloom.b * (1 - _SourceBloomHighlightSuppression) > 0.3 ? adjustedBloom.b : bloom.b);
            float3 combined = exposed - EFSourceBloomThreshold(exposed) * _SourceBloomHighlightSuppression + bloom * _BloomTint.rgb;
            combined = lerp(exposed, combined, _BloomIntensity);
            combined *= EFSourceDisplayVignette(input.uv);
            // LUT本身为实时producer。输出保持线性，交给Unity目标的sRGB转换。
            return float4(EFSourceDisplayLut(combined * _ColorLutParams.w), 1);
        }
        float4 CopyFragment(EFFullscreenVaryings input) : SV_Target
        {
            return float4(EFSource(EFSourceUV(input.uv)), 1);
        }
        float4 SourceUIBlurFragment(EFFullscreenVaryings input) : SV_Target
        {
            float2 uv = EFSourceUV(input.uv);
            // SI1_2123/2132先限制单样本高亮，再进行二项9×9核；2.5是高亮阈值。
            const float offsets[9] = {-4,-3,-2,-1,0,1,2,3,4};
            const float weights[9] = {1.0/256,8.0/256,28.0/256,56.0/256,70.0/256,56.0/256,28.0/256,8.0/256,1.0/256};
            float3 sum = 0;
            [unroll] for (int y = 0; y < 9; y++)
                [unroll] for (int x = 0; x < 9; x++)
                {
                    float3 color = EFSource(uv + float2(offsets[x], offsets[y]) * _SourceTexture_TexelSize.xy);
                    float brightness = max(color.r, max(color.g, color.b));
                    color *= _UIBlurHighlightClamp / max(brightness, _UIBlurHighlightClamp);
                    color = f16tof32(f32tof16(color));
                    sum += color * weights[x] * weights[y];
                }
            return float4(sum, 1);
        }
        ENDHLSL
        Pass
        {
            Name "Final"
            HLSLPROGRAM
            #pragma vertex EFFullscreenVertex
            #pragma fragment FinalFragment
            ENDHLSL
        }
        Pass
        {
            Name "BloomPrefilter"
            HLSLPROGRAM
            #pragma vertex EFFullscreenVertex
            #pragma fragment PrefilterFragment
            ENDHLSL
        }
        Pass
        {
            Name "BloomBlur"
            HLSLPROGRAM
            #pragma vertex EFFullscreenVertex
            #pragma fragment BlurFragment
            ENDHLSL
        }
        Pass
        {
            Name "Debug"
            HLSLPROGRAM
            #pragma vertex EFFullscreenVertex
            #pragma fragment DebugFragment
            ENDHLSL
        }
        Pass
        {
            Name "SourceDepthOfField"
            HLSLPROGRAM
            #pragma vertex EFFullscreenVertex
            #pragma fragment DofFragment
            ENDHLSL
        }
        Pass
        {
            Name "SourceSceneDisplay"
            HLSLPROGRAM
            #pragma vertex EFFullscreenVertex
            #pragma fragment SourceDisplayFragment
            ENDHLSL
        }
        Pass
        {
            Name "SourceBloomPrefilter"
            HLSLPROGRAM
            #pragma vertex EFFullscreenVertex
            #pragma fragment SourceBloomPrefilter
            ENDHLSL
        }
        Pass
        {
            Name "SourceBloomDownsample"
            HLSLPROGRAM
            #pragma vertex EFFullscreenVertex
            #pragma fragment SourceBloomDownsample
            ENDHLSL
        }
        Pass
        {
            Name "SourceBloomUpsample"
            HLSLPROGRAM
            #pragma vertex EFFullscreenVertex
            #pragma fragment SourceBloomUpsample
            ENDHLSL
        }
        Pass
        {
            Name "Copy"
            HLSLPROGRAM
            #pragma vertex EFFullscreenVertex
            #pragma fragment CopyFragment
            ENDHLSL
        }
        Pass
        {
            Name "SourceUIBlur"
            HLSLPROGRAM
            #pragma vertex EFFullscreenVertex
            #pragma fragment SourceUIBlurFragment
            ENDHLSL
        }
    }
}
