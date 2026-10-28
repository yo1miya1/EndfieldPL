Shader "Endfield/InkEffect"
{
    Properties
    {
        _InkBaseMap ("主墨纹", 2D) = "white" {}
        _InkMaskMap ("乘法遮罩", 2D) = "white" {}
        _InkOverlayMap ("叠色纹理", 2D) = "black" {}
        _InkNoiseMap ("扭曲噪声", 2D) = "bump" {}
        _InkBaseTint ("主墨纹颜色", Color) = (0,0,0,1)
        _InkOverlayTint ("叠色颜色", Color) = (1,1,1,1)
        _InkBaseUVTransform ("主纹理UV缩放偏移", Vector) = (1,1,0,0)
        _InkBaseUVRotation ("主纹理UV二维旋转", Vector) = (1,0,0,1)
        _InkBaseUVVelocity ("主纹理UV时间/顶点相位速度", Vector) = (0,0,0,0)
        _InkBaseUVWeights ("主纹理UV流混合", Vector) = (1,0,0,0)
        _InkMaskUVTransform ("遮罩UV缩放偏移", Vector) = (1,1,0,0)
        _InkMaskUVRotation ("遮罩UV二维旋转", Vector) = (1,0,0,1)
        _InkMaskUVVelocity ("遮罩UV时间/顶点相位速度", Vector) = (0,0,0,0)
        _InkMaskUVWeights ("遮罩UV流混合", Vector) = (1,0,0,0)
        _InkOverlayUVTransform ("叠色UV缩放偏移", Vector) = (1,1,0,0)
        _InkOverlayUVRotation ("叠色UV二维旋转", Vector) = (1,0,0,1)
        _InkOverlayUVVelocity ("叠色UV时间/顶点相位速度", Vector) = (0,0,0,0)
        _InkOverlayUVWeights ("叠色UV流混合", Vector) = (1,0,0,0)
        _InkNoiseUVTransform ("噪声UV缩放偏移", Vector) = (1,1,0,0)
        _InkNoiseUVRotation ("噪声UV二维旋转", Vector) = (1,0,0,1)
        _InkNoiseUVVelocity ("噪声UV时间/顶点相位速度", Vector) = (0,0,0,0)
        _InkNoiseUVWeights ("噪声UV流混合", Vector) = (1,0,0,0)
        _InkNoiseResponse ("噪声偏移/法线模式/XY强度", Vector) = (0,1,.5,0)
        _InkProjectionParams ("投影纵轴/距离混合/相对混合/开关", Vector) = (0,0,1,0)
        _InkProjectionOriginOS ("墨纹投影中心（对象局部）", Vector) = (0,0,0,1)
        _InkProjectionSign ("源视图基底符号", Vector) = (1,1,0,0)
        _InkDepthRanges ("深度淡出近起近止远起远止", Vector) = (.001,10,120,100)
        _InkUVStreamBlend ("主UV替代流权重", Float) = 0
        _InkPhase ("墨纹动画相位", Float) = 0
        _InkAnimationSpeed ("墨纹相位时钟速度", Float) = 0
        _InkMipBias ("源mip偏移", Float) = 0
        _InkIgnoreVertexColor ("主墨纹覆盖顶点色", Float) = 0
        _InkColorGain ("主墨纹颜色增益", Float) = 1
        _InkAlphaGain ("主墨纹覆盖率增益", Float) = 1
        _InkBaseMonochrome ("主墨纹单色混合", Float) = 1
        _InkBaseDistortion ("主墨纹扭曲量", Float) = 0
        _InkMaskMonochrome ("遮罩单色混合", Float) = 1
        _InkMaskDistortion ("遮罩扭曲量", Float) = 0
        _InkOverlayDistortion ("叠色扭曲量", Float) = 0
        _InkOverlayIgnoreVertexColor ("叠色覆盖顶点色", Float) = 0
        _InkDepthFadeEnabled ("深度淡出开关", Float) = 0
        _InkInstanceOpacity ("实例覆盖率", Float) = 1
        _InkLODFade ("实例LOD阈值", Float) = 1000
        _InkAlphaMode ("源Alpha模式", Float) = 0
        _InkPreExposureWeight ("预曝光混合", Float) = 0
        _InkCutoff ("源覆盖率裁剪阈值", Float) = 0
        _InkSoftIntersectionDistance ("交界淡出距离", Float) = 0
        _InkSoftIntersectionOffset ("交界淡出偏移", Float) = 0
        _InkEdgeTint ("轮廓叠色RGBA", Color) = (1,1,1,0)
        _InkEdgeParams ("轮廓偏移/覆盖率权重/幂次/正反混合", Vector) = (0,0,1,1)
        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("剔除", Float) = 0
        [HideInInspector] _SrcBlend ("源混合", Float) = 1
        [HideInInspector] _DstBlend ("目标混合", Float) = 10
        [HideInInspector] _ZWrite ("深度写入", Float) = 0
        [HideInInspector] _ColorMask ("颜色写入掩码", Float) = 15
    }
    SubShader
    {
        Tags { "RenderPipeline"="EndfieldPipeline" "RenderType"="Transparent" "Queue"="Transparent" }
        Pass
        {
            Name "InkForward"
            Tags { "LightMode"="EndfieldForward" }
            Cull [_Cull] ZWrite [_ZWrite] Blend [_SrcBlend] [_DstBlend] ZTest LEqual
            ColorMask [_ColorMask]
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vertex
            #pragma fragment Fragment
            #pragma shader_feature_local _ EF_INK_ALPHA_CLIP
            #pragma shader_feature_local _ EF_INK_TWO_LAYER
            #pragma shader_feature_local _ EF_INK_EDGE_TINT
            #include "Library/Coordinates.hlsl"
            TEXTURE2D(_InkBaseMap); SAMPLER(sampler_InkBaseMap);
            TEXTURE2D(_InkMaskMap); SAMPLER(sampler_InkMaskMap);
            TEXTURE2D(_InkOverlayMap); SAMPLER(sampler_InkOverlayMap);
            TEXTURE2D(_InkNoiseMap); SAMPLER(sampler_InkNoiseMap);
            TEXTURE2D(_CameraDepthTexture); SAMPLER(sampler_PointClamp);
            CBUFFER_START(UnityPerMaterial)
            float4 _InkBaseTint, _InkOverlayTint;
            float4 _InkBaseUVTransform, _InkBaseUVRotation, _InkBaseUVVelocity, _InkBaseUVWeights;
            float4 _InkMaskUVTransform, _InkMaskUVRotation, _InkMaskUVVelocity, _InkMaskUVWeights;
            float4 _InkOverlayUVTransform, _InkOverlayUVRotation, _InkOverlayUVVelocity, _InkOverlayUVWeights;
            float4 _InkNoiseUVTransform, _InkNoiseUVRotation, _InkNoiseUVVelocity, _InkNoiseUVWeights;
            float4 _InkNoiseResponse, _InkProjectionParams, _InkProjectionOriginOS, _InkProjectionSign, _InkDepthRanges;
            float _InkUVStreamBlend, _InkPhase, _InkAnimationSpeed, _InkMipBias;
            float _InkIgnoreVertexColor, _InkColorGain, _InkAlphaGain, _InkBaseMonochrome;
            float _InkBaseDistortion, _InkMaskMonochrome, _InkMaskDistortion, _InkOverlayDistortion;
            float _InkOverlayIgnoreVertexColor, _InkDepthFadeEnabled, _InkInstanceOpacity, _InkLODFade;
            float _InkAlphaMode, _InkPreExposureWeight, _InkCutoff, _Cull, _SrcBlend, _DstBlend, _ZWrite, _ColorMask;
            float _InkSoftIntersectionDistance, _InkSoftIntersectionOffset;
            float4 _InkEdgeTint, _InkEdgeParams;
            CBUFFER_END
            float _EndfieldSceneExposure;
            float4 _EndfieldScreenSize;
            float4 _Time;
            struct Attributes
            {
                float3 positionOS : POSITION;
                float3 normalOS : NORMAL;
                float2 uv0 : TEXCOORD0;
                float2 uv1 : TEXCOORD1;
                float2 uv2 : TEXCOORD2;
                float2 uv3 : TEXCOORD3;
                float4 color : COLOR;
            };
            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float4 uvMain : TEXCOORD0;
                float4 uvAlternate : TEXCOORD1;
                float3 positionWS : TEXCOORD2;
                float3 normalWS : TEXCOORD3;
                float4 color : COLOR;
            };
            Varyings Vertex(Attributes input)
            {
                Varyings o;
                o.positionWS = EFWorldPosition(input.positionOS);
                o.positionCS = EFClipPosition(o.positionWS);
                o.uvMain = float4(input.uv0, input.uv1);
                o.uvAlternate = float4(input.uv2, input.uv3);
                // 源postVS o5是已经乘过实例/粒子衰减的颜色，不能改用原COLOR。
                o.color = input.color;
                o.normalWS = EFWorldNormal(input.normalOS);
                return o;
            }
            float2 LayerUV(float2 mainUV, float2 alternateUV, float2 projection, float phase, float vertexPhase,
                           float4 transform, float4 rotation, float4 velocity, float4 weights)
            {
                float4 uv = mainUV.xxyy * weights.x + alternateUV.xxyy * weights.y + projection.xxyy * weights.w;
                uv += velocity.xxyy * phase + velocity.zzww * vertexPhase;
                uv = (uv - 0.5) * rotation;
                return (uv.xy + uv.zw + 0.5) * transform.xy + transform.zw;
            }
            float4 Fragment(Varyings input, bool frontFace : SV_IsFrontFace) : SV_Target
            {
                // SI1_1571/1589 原共用四纹理模型。每层旋转/相位/UV流均使用真实材质配置。
                float phase = _InkPhase + _Time.y * _InkAnimationSpeed;
                float2 alternate = lerp(input.uvAlternate.xy, input.uvMain.zw, _InkUVStreamBlend);
                float2 projection = 0;
                if (_InkProjectionParams.w > 0.5)
                {
                    float3 origin = EFWorldPosition(_InkProjectionOriginOS.xyz);
                    float3 relative = input.positionWS - origin;
                    float2 cameraPlane = mul((float3x3)unity_MatrixV, relative).xy * _InkProjectionSign.xy;
                    float2 ndc = input.positionCS.xy * _EndfieldScreenSize.zw * 2 - 1;
                    ndc.y *= _EndfieldScreenSize.y / _EndfieldScreenSize.x;
                    projection = lerp(ndc, cameraPlane, _InkProjectionParams.z);
                    if (_InkProjectionParams.x != 0) projection.y = input.positionWS.y;
                    float originDepth = -mul(unity_MatrixV, float4(origin, 1)).z - _ProjectionParams.y;
                    projection *= lerp(1, max(1, originDepth), _InkProjectionParams.y);
                }
                float vertexPhaseBase = _InkUVStreamBlend * input.uvAlternate.x;
                float vertexPhaseOther = _InkUVStreamBlend * input.uvAlternate.y;
                float2 noiseUV = LayerUV(input.uvMain.xy, alternate, projection, phase, vertexPhaseOther,
                    _InkNoiseUVTransform, _InkNoiseUVRotation, _InkNoiseUVVelocity, _InkNoiseUVWeights);
                // 每层使用自己的原生采样器：按源分别发布U/V ClampEdge或Wrap，Bilinear保留point mip。
                float4 noise = SAMPLE_TEXTURE2D_BIAS(_InkNoiseMap, sampler_InkNoiseMap, noiseUV, _InkMipBias);
                float height = noise.r * (1 + _InkNoiseResponse.x) - _InkNoiseResponse.x;
                float2 distortion = _InkNoiseResponse.zw * height;
                if (_InkNoiseResponse.y != 0) distortion = (float2(noise.a * height, noise.g) * 2 - 1) * _InkNoiseResponse.z;
                float2 baseUV = LayerUV(input.uvMain.xy, alternate, projection, phase, vertexPhaseBase,
                    _InkBaseUVTransform, _InkBaseUVRotation, _InkBaseUVVelocity, _InkBaseUVWeights) + distortion * _InkBaseDistortion;
                float2 maskUV = LayerUV(input.uvMain.xy, alternate, projection, phase, vertexPhaseOther,
                    _InkMaskUVTransform, _InkMaskUVRotation, _InkMaskUVVelocity, _InkMaskUVWeights) + distortion * _InkMaskDistortion;
                float4 baseSample = SAMPLE_TEXTURE2D_BIAS(_InkBaseMap, sampler_InkBaseMap, baseUV, _InkMipBias);
                float4 maskSample = SAMPLE_TEXTURE2D_BIAS(_InkMaskMap, sampler_InkMaskMap, maskUV, _InkMipBias);
                baseSample = lerp(baseSample, float4(1,1,1,baseSample.r), _InkBaseMonochrome);
                maskSample = lerp(maskSample, float4(1,1,1,maskSample.r), _InkMaskMonochrome);
                float4 baseColor = lerp(input.color, 1, _InkIgnoreVertexColor) * _InkBaseTint * float4(_InkColorGain.xxx, _InkAlphaGain);
                baseSample *= baseColor;
                float4 masked = baseSample * maskSample;
                float edgeResponse = 0;
                #if defined(EF_INK_EDGE_TINT)
                    // 源双层笔刷：以实际世界法线/当前观察方向计算边缘色和覆盖率。
                    float3 n = frontFace ? normalize(input.normalWS) : -normalize(input.normalWS);
                    float3 view = normalize(_WorldSpaceCameraPos - input.positionWS);
                    edgeResponse = exp2(log2(saturate(_InkEdgeParams.x + dot(view, n))) * _InkEdgeParams.z);
                    edgeResponse = lerp(1 - edgeResponse, edgeResponse, _InkEdgeParams.w);
                    masked.a *= lerp(1, edgeResponse, _InkEdgeParams.y);
                #endif
                float depthFade = 1;
                if (_InkDepthFadeEnabled != 0)
                {
                    float depth = abs(mul(unity_MatrixV, float4(input.positionWS,1)).z);
                    depthFade = saturate((depth-_InkDepthRanges.x)/(_InkDepthRanges.y-_InkDepthRanges.x));
                    depthFade *= saturate((depth-_InkDepthRanges.z)/(_InkDepthRanges.w-_InkDepthRanges.z));
                }
                float noiseLOD = frac(52.9829178 * frac(dot(floor(input.positionCS.xy * 0.5), float2(0.0671105608,0.00583714992))));
                float signedNoise = _InkLODFade >= 0 ? noiseLOD : -noiseLOD;
                float lod = min(_InkLODFade - signedNoise, _InkInstanceOpacity - noiseLOD) > 0 ? 1 : 0;
                float alpha = saturate(masked.a * depthFade * _InkInstanceOpacity * lod);
                if (_InkSoftIntersectionDistance > 0)
                {
                    // 源1554：场景深度与当前粒子view-depth之差；采本帧opaque快照，不回采DSV。
                    float2 screenUV = input.positionCS.xy * _EndfieldScreenSize.zw;
                    float sceneDepth = SAMPLE_TEXTURE2D_LOD(_CameraDepthTexture, sampler_PointClamp, screenUV, 0).r;
                    float3 sceneWorld = EFReconstructWorld(screenUV, sceneDepth);
                    float sceneViewDepth = abs(mul(unity_MatrixV, float4(sceneWorld, 1)).z);
                    float particleViewDepth = abs(mul(unity_MatrixV, float4(input.positionWS, 1)).z);
                    alpha *= saturate((sceneViewDepth - particleViewDepth + _InkSoftIntersectionOffset) / _InkSoftIntersectionDistance);
                }
                #if defined(EF_INK_ALPHA_CLIP)
                    clip(alpha - _InkCutoff);
                #endif
                float3 color = masked.rgb;
                #if !defined(EF_INK_TWO_LAYER)
                float4 overlayTint = lerp(input.color, 1, _InkOverlayIgnoreVertexColor) * _InkOverlayTint;
                float2 overlayUV = LayerUV(input.uvMain.xy, alternate, projection, phase, vertexPhaseOther,
                    _InkOverlayUVTransform, _InkOverlayUVRotation, _InkOverlayUVVelocity, _InkOverlayUVWeights) + distortion * _InkOverlayDistortion;
                float4 overlay = SAMPLE_TEXTURE2D_BIAS(_InkOverlayMap, sampler_InkOverlayMap, overlayUV, _InkMipBias);
                float overlayCoverage = saturate((baseSample.a * maskSample.a + overlay.a) * overlayTint.a);
                color += overlay.rgb * overlayCoverage * overlayTint.rgb;
                #endif
                #if defined(EF_INK_EDGE_TINT)
                    color = lerp(color, _InkEdgeTint.rgb, _InkEdgeTint.a * edgeResponse);
                #endif
                color *= lerp(1, _EndfieldSceneExposure, _InkPreExposureWeight);
                color = clamp(color, 0, 1000);
                return float4(color * alpha, (1 - _InkAlphaMode) * alpha);
            }
            ENDHLSL
        }
    }
}
