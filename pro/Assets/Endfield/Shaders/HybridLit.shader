Shader "Endfield/HybridLit"
{
    Properties
    {
        [MainTexture] _BaseMap ("基础颜色贴图", 2D) = "white" {}
        [MainColor] _BaseColor ("基础颜色", Color) = (1,1,1,1)
        [Toggle(EF_NORMAL_MAP)] _UseNormalMap ("使用切线法线", Float) = 0
        [Normal] _NormalMap ("法线贴图", 2D) = "bump" {}
        _NormalScale ("法线强度", Range(0,2)) = 1
        [Toggle(EF_MASK_MAP)] _UseMaskMap ("使用语义遮罩（非原ILM）", Float) = 0
        _MaskMap ("金属R / 粗糙G / 遮蔽B", 2D) = "white" {}
        _Metallic ("金属度", Range(0,1)) = 0
        _Roughness ("粗糙度", Range(0.04,1)) = 0.6
        _Occlusion ("遮蔽权重", Range(0,1)) = 1
        _Specular ("介质高光", Range(0,1)) = 0.5
        _NprWeight ("NPR混合权重（诊断基线）", Range(0,1)) = 0
        _EmissionMap ("自发光贴图", 2D) = "white" {}
        [HDR] _EmissionColor ("自发光颜色", Color) = (0,0,0,1)
        [Toggle(EF_ALPHA_CLIP)] _AlphaClip ("透明裁剪", Float) = 0
        _Cutoff ("裁剪阈值", Range(0,1)) = 0.5
        [Toggle(EF_HAIR)] _Hair ("头发家族", Float) = 0
        [Toggle(EF_CLOTH)] _Cloth ("衣物家族", Float) = 0
        [Toggle(EF_FACE)] _Face ("面部家族", Float) = 0
        [Toggle(EF_EYE)] _Eye ("眼睛家族", Float) = 0
        _OutlineColor ("描边颜色", Color) = (0.035,0.025,0.03,1)
        _OutlineWidth ("描边宽度（世界单位）", Range(0,0.02)) = 0
        [Toggle(EF_SOURCE_SCREEN_OUTLINE)] _SourceScreenOutline ("源屏幕空间描边", Float) = 0
        _SourceOutlineWidth ("屏幕轮廓宽度", Float) = 0
        _SourceOutlineDepth ("轮廓深度偏移", Float) = 0
        _SourceOutlineSmoothNormal ("使用轮廓平滑法线", Float) = 0
        _SourceOutlineWidthMap ("轮廓宽度R/深度G", 2D) = "white" {}
        _SourceOutlineCoverageMap ("轮廓覆盖率R", 2D) = "white" {}
        _SourceOutlineCutoff ("轮廓裁剪阈值", Float) = 0.5
        [Enum(Unprotected,0,Protected,16)] _OutlineStencilReference ("轮廓遮挡区域", Float) = 0
        [Enum(UnityEngine.Rendering.CompareFunction)] _OutlineStencilComparison ("轮廓遮挡比较", Float) = 8
        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("剔除", Float) = 2
        [HideInInspector] _SrcBlend ("源混合", Float) = 1
        [HideInInspector] _DstBlend ("目标混合", Float) = 0
        [HideInInspector] _ZWrite ("深度写入", Float) = 1
        [Toggle(EF_SOURCE_CHARACTER)] _SourceCharacter ("源角色GBuffer/表面受光", Float) = 0
        [Toggle(EF_SOURCE_VIEW_TINT)] _SourceViewTint ("源视角染色", Float) = 0
        [Toggle(EF_SOURCE_COVERAGE)] _SourceCoverage ("源覆盖率裁剪", Float) = 0
        _CoverageMap ("覆盖率R", 2D) = "white" {}
        _SourceInstancePayload ("源实例字段（解码10/10/10/2）", Vector) = (0,0,0,0)
        [HideInInspector] _CharacterShadowIndex ("Character Shadow Index", Float) = -1
        _SourceGBufferTag ("源表面标签", Float) = 0
        _BackFaceNormal ("源背面法线混合", Float) = 0
        _SourceMipBias ("源材质Mip偏移", Float) = 0
        _ViewTintStrength ("视角染色强度", Float) = 0
        _ViewTintColor ("视角染色颜色", Color) = (1,1,1,1)
        [Toggle(EF_SOURCE_PACKED_MASK)] _SourcePackedMask ("源金属/高光/细节/光滑遮罩", Float) = 0
        [Toggle(EF_SOURCE_COLOR_LUT)] _SourceColorLut ("源基础色响应LUT", Float) = 0
        [Toggle(EF_SOURCE_SKIN)] _SourceSkin ("皮肤区域与面部SDF", Float) = 0
        [Toggle(EF_SOURCE_ENVIRONMENT_REFLECTION)] _SourceEnvironmentReflection ("Unity探针环境镜面", Float) = 0
        [Toggle(EF_SOURCE_PARALLAX_GLOW)] _SourceParallaxGlow ("视差水晶附加响应", Float) = 0
        _SourceMaskMap ("源遮罩R金属G高光B细节A光滑", 2D) = "white" {}
        _LightingRamp ("源明暗Ramp", 2D) = "white" {}
        _AlbedoResponseLut ("源基础色响应LUT", 2D) = "white" {}
        _SourceIndirectAlbedoGain ("间接基础色增益", Float) = 1
        _SourceIndirectSaturation ("间接基础色饱和度", Float) = 1
        _SourceRampBias ("源Ramp偏移", Float) = 0
        _SourceIndirectStrength ("源间接受光强度", Float) = 1
        _SourceDiffuseStrength ("源漫反射强度", Float) = 1
        _SourceSpecularStrength ("源高光强度", Float) = 1
        _SourceShadowStrength ("源遮蔽混合", Float) = 1
        _SourceAmbientTint ("源材质环境风格乘色", Color) = (1,1,1,1)
        _SourceHemisphereDirection ("源环境明暗轴", Vector) = (0,1,0,0)
        _SourceHemisphereParams ("源环境明暗偏移/缩放/底值", Vector) = (0,1,0,0)
        _SourceEnvironmentRotation ("环境反射旋转余弦/正弦", Vector) = (0,1,0,0)
        _SourceAmbientResponse ("环境响应权重", Float) = 1
        _SourceDirectColorWeight ("主光颜色响应", Float) = 1
        _SourceEnvironmentStrength ("环境镜面响应强度", Float) = 1
        _HairViewAlignmentPower ("发丝视角对齐指数", Float) = 1
        _HairRightOS ("发丝局部右轴", Vector) = (1,0,0,0)
        _HairForwardOS ("发丝局部前轴", Vector) = (0,0,1,0)
        _HairOcclusionMap ("发丝分层遮蔽R", 2D) = "white" {}
        _HairOcclusionLobe ("遮蔽瓣条带频率/偏移/光滑/最小响应", Vector) = (0,0.5,1,0)
        _HairOcclusionResponse ("遮蔽饱和度/条带遮罩混合", Vector) = (1,1,0,0)
        _HairOcclusionMap_ST ("分层遮蔽UV变换", Vector) = (1,1,0,0)
        _SkinRegionMap ("皮肤区域/面部/染色遮罩", 2D) = "white" {}
        _SkinLightingSdf ("面部双侧受光SDF", 2D) = "white" {}
        _SkinRightOS ("皮肤局部右轴", Vector) = (1,0,0,0)
        _SkinForwardOS ("皮肤局部前轴", Vector) = (0,0,1,0)
        _SkinViewTintStrength ("皮肤双区域视角染色强度", Vector) = (0,0,0,0)
        _SkinHemisphereOriginOS ("皮肤半球中心（物体空间）", Vector) = (0,0,0,0)
        _SkinSpecularMap ("皮肤独立高光响应", 2D) = "black" {}
        _SkinSpecularParallax ("皮肤高光视差XY", Vector) = (0,0,0,0)
        _SkinSdfBias ("皮肤SDF明暗偏移", Float) = 0
        _ParallaxGlowMap ("水晶高度/附加响应R", 2D) = "black" {}
        _ParallaxGlowParams ("视差步数/深度/扰动法线开关", Vector) = (1,0,0,0)
        _ParallaxGlowColor ("视差附加颜色", Color) = (0,0,0,1)
        [Toggle(EF_SOURCE_ENVIRONMENT)] _SourceEnvironment ("源环境材质", Float) = 0
        _EnvironmentMaskMap ("源环境金属R粗糙G遮蔽B", 2D) = "white" {}
        _EnvironmentBaseUV_ST ("环境基础色UV变换", Vector) = (1,1,0,0)
        _EnvironmentMaterialUV_ST ("环境材质UV变换", Vector) = (1,1,0,0)
        _EnvironmentRoughnessRange ("环境粗糙度范围", Vector) = (0,1,0,0)
        _EnvironmentAlbedoUVWeight ("基础色UV1混合", Float) = 0
        _EnvironmentMaterialUVWeight ("材质UV1混合", Float) = 0
        _EnvironmentMetallicOverrideWeight ("金属覆盖控制", Float) = 0
        _EnvironmentMetallicOverride ("金属覆盖值", Float) = 0
        _EnvironmentBaseGain ("基础色增益", Float) = 1
        _EnvironmentBaseBlend ("基础色常量混合", Float) = 0
        _EnvironmentSpecularRoughnessWeight ("粗糙镜面混合", Float) = 0
        _EnvironmentSpecularBias ("镜面偏移", Float) = 0
        _EnvironmentSpecularMetallicWeight ("金属镜面混合", Float) = 0
        _EnvironmentLightingWeight ("环境光照权重", Float) = 0
        _EnvironmentReflectionMask ("反射关闭混合", Float) = 0
        _EnvironmentMotionDisabled ("源运动禁用", Float) = 0
        _EnvironmentNormalMipBias ("环境法线Mip偏移", Float) = 0
        _EnvironmentMaterialTag ("环境材质分类", Float) = 0
        _HairMaskMap ("发丝遮罩", 2D) = "white" {}
        _HairNormalMap ("发丝双层法线", 2D) = "bump" {}
        _HairSpecularRamp ("发丝主瓣高光Ramp", 2D) = "white" {}
        _HairPrimarySecondaryShift ("主次发丝偏移", Vector) = (0.5,0.5,0,0)
        _HairSecondaryColor ("次发丝高光颜色", Color) = (1,1,1,1)
        _HairPrimaryStrength ("主发丝高光强度", Float) = 1
        _HairSecondarySmoothness ("次发丝光滑度", Float) = 0.5
        _HairFlowDirection ("物体局部发丝流向", Float) = 0
        _HairDetailNormalScale ("发丝细节法线强度", Float) = 1
        [Toggle(EF_SOURCE_EFFECT)] _SourceEffect ("源效果材质", Float) = 0
        _EffectVertexColor ("源常量顶点颜色", Color) = (1,1,1,1)
        _EffectColor ("效果颜色", Color) = (1,1,1,1)
        _EffectDissolveColor ("溶解边缘颜色", Color) = (0,0,0,0)
        _EffectDepthRanges ("近起近止远起远止", Vector) = (0.001,10,120,100)
        _EffectDissolveProfile ("溶解边缘缩放/偏移/宽度/影响", Vector) = (1,0,0,0)
        _EffectColorResponse ("效果颜色响应RGB/饱和度A", Vector) = (1,1,1,1)
        _EffectIgnoreVertexColor ("覆盖顶点颜色", Float) = 0
        _EffectColorIntensity ("效果颜色增益", Float) = 1
        _EffectAlphaIntensity ("效果覆盖率增益", Float) = 1
        _EffectMonochromeWeight ("效果单色混合", Float) = 0
        _EffectMipBias ("效果额外Mip偏移", Float) = 0
        _EffectInvisibleWeight ("效果隐藏混合", Float) = 0
        _EffectDissolveEnabled ("溶解开关", Float) = 0
        _EffectDissolveMask ("溶解遮罩混合", Float) = 0
        _EffectDissolveStrength ("溶解强度", Float) = 0
        _EffectDissolveHeight ("溶解高度", Float) = 0
        _EffectBloomThreshold ("效果亮部起点", Float) = 1
        _EffectBloomBoost ("效果亮部增益", Float) = 0
        _EffectPreExposureWeight ("效果预曝光混合", Float) = 0
        _EffectDepthFadeEnabled ("效果深度淡出", Float) = 0
        _EffectInstanceOpacity ("效果实例覆盖率", Float) = 1
        _EffectOpacity ("效果整体覆盖率", Float) = 1
        _EffectAlphaMode ("效果Alpha模式", Float) = 0
        _EffectColorResponseWeight ("效果颜色响应混合", Float) = 0
        _EyeReflectionMap ("源角膜反射贴图", 2D) = "black" {}
        _EyeIrisTint ("虹膜染色", Color) = (1,1,1,1)
        _EyeScleraTint ("眼白染色", Color) = (1,1,1,1)
        _EyeReflectionColor ("角膜反射Alpha染色", Color) = (1,1,1,1)
        _EyeReflectionStrength ("角膜反射RGB强度", Float) = 1
        _EyeParallax ("虹膜视差", Float) = 0
        _EyeCurvature ("角膜曲率", Float) = 0
        [Toggle(EF_SOURCE_ANISOTROPIC)] _SourceAnisotropic ("源双瓣各向异性/coat", Float) = 0
        _ClothAnisotropy ("双瓣各向异性/视角偏移/镜面重映射", Vector) = (0,0,0,1)
        _ClothTangentMode ("衣料方向基底（0网格/1几何法线）", Float) = 0
        _ClothSecondLobeColor ("第二高光瓣颜色", Color) = (0,0,0,1)
        _ClothCoatColor ("coat反射色", Color) = (1,1,1,1)
        _ClothCoatSmoothness ("coat光滑度", Float) = 0
        _ClothCoatMetallic ("coat金属权重", Float) = 0
        _ClothCoatNormalBlend ("coat法线混合", Float) = 1
        _ClothCoatMaskMap ("coat覆盖率R", 2D) = "black" {}
        _ClothCoatReflectanceMap ("coat反射查表", 2D) = "white" {}
        [Toggle(EF_SOURCE_STOCHASTIC_SHADOW)] _SourceStochasticShadow ("源随机覆盖率阴影", Float) = 0
        _AlphaMap ("阴影覆盖率Alpha", 2D) = "white" {}
        _Opacity ("阴影覆盖率强度", Float) = 1
    }
    SubShader
    {
        Tags { "RenderPipeline"="EndfieldPipeline" "RenderType"="Opaque" "Queue"="Geometry" }
        HLSLINCLUDE
        #pragma target 4.5
        #include "Library/Surface.hlsl"
        ENDHLSL
        Pass
        {
            Name "GBuffer"
            Tags { "LightMode"="EndfieldGBuffer" }
            // bit4只表示不允许头发与其轮廓越过的表面；不继承源未使用的Stencil位。
            Stencil { Ref [_OutlineStencilReference] ReadMask 16 WriteMask 16 Comp [_OutlineStencilComparison] Pass Replace }
            Cull [_Cull] ZWrite On ZTest LEqual
            HLSLPROGRAM
            #pragma vertex EFVertex
            #pragma fragment Fragment
            #pragma shader_feature_local _ EF_HAIR EF_CLOTH EF_FACE EF_EYE
            #pragma shader_feature_local _ EF_NORMAL_MAP
            #pragma shader_feature_local _ EF_MASK_MAP
            #pragma shader_feature_local _ EF_ALPHA_CLIP
            #pragma shader_feature_local _ EF_SOURCE_CHARACTER
            #pragma shader_feature_local _ EF_SOURCE_VIEW_TINT
            #pragma shader_feature_local _ EF_SOURCE_COVERAGE
            #pragma shader_feature_local _ EF_SOURCE_ENVIRONMENT
            #pragma shader_feature_local _ EF_SOURCE_EFFECT
            EFGBufferOutput Fragment(EFVaryings input, bool frontFace : SV_IsFrontFace)
            {
                // 尚无蒙皮/对象前帧流，因此此处只输出已明确支持的相机运动。
                float4 previousClip = mul(_EndfieldPreviousViewProjection, float4(input.positionWS, 1));
                float2 motion = (input.currentClip.xy / max(input.currentClip.w, 1e-8) - previousClip.xy / max(previousClip.w, 1e-8)) * float2(0.5, -0.5);
                #if defined(EF_SOURCE_CHARACTER)
                    return EFSourceCharacterGBuffer(input, frontFace, motion * _EndfieldHistoryValid);
                #elif defined(EF_SOURCE_ENVIRONMENT)
                    return EFSourceEnvironmentGBuffer(input, frontFace, motion * _EndfieldHistoryValid);
                #elif defined(EF_SOURCE_EFFECT)
                    clip(-1);
                    return (EFGBufferOutput)0;
                #else
                    return EFEncodeGBuffer(EFSampleSurface(input, frontFace), motion * _EndfieldHistoryValid);
                #endif
            }
            ENDHLSL
        }
        Pass
        {
            Name "Forward"
            Tags { "LightMode"="EndfieldForward" }
            Cull [_Cull] Blend [_SrcBlend] [_DstBlend] ZWrite [_ZWrite] ZTest LEqual
            HLSLPROGRAM
            #pragma vertex EFVertex
            #pragma fragment Fragment
            #pragma shader_feature_local _ EF_HAIR EF_CLOTH EF_FACE EF_EYE
            #pragma shader_feature_local _ EF_NORMAL_MAP
            #pragma shader_feature_local _ EF_MASK_MAP
            #pragma shader_feature_local _ EF_ALPHA_CLIP
            #pragma shader_feature_local _ EF_SOURCE_CHARACTER
            #pragma shader_feature_local _ EF_SOURCE_VIEW_TINT
            #pragma shader_feature_local _ EF_SOURCE_COVERAGE
            #pragma shader_feature_local _ EF_SOURCE_PACKED_MASK
            #pragma shader_feature_local _ EF_SOURCE_COLOR_LUT
            #pragma shader_feature_local _ EF_SOURCE_ANISOTROPIC
            #pragma shader_feature_local _ EF_SOURCE_ENVIRONMENT_REFLECTION
            #pragma shader_feature_local _ EF_SOURCE_SKIN
            #pragma shader_feature_local _ EF_SOURCE_PARALLAX_GLOW
            #include "Library/SourceCharacterLighting.hlsl"
            float4 Fragment(EFVaryings input, bool frontFace : SV_IsFrontFace) : SV_Target
            {
                EFSurface s = EFSampleSurface(input, frontFace);
                #if defined(EF_SOURCE_CHARACTER)
                    return float4(EFEvaluateSourceCharacter(input,frontFace),s.alpha);
                #else
                    return float4(EFEvaluateLighting(s, input.positionWS), s.alpha);
                #endif
            }
            ENDHLSL
        }
        Pass
        {
            Name "SurfaceLighting"
            Tags { "LightMode"="EndfieldSurfaceLighting" }
            Stencil { Ref [_OutlineStencilReference] ReadMask 16 WriteMask 0 Comp [_OutlineStencilComparison] Pass Keep }
            Cull [_Cull] ZWrite Off ZTest Equal
            HLSLPROGRAM
            #pragma vertex EFVertex
            #pragma fragment Fragment
            #pragma shader_feature_local _ EF_HAIR EF_CLOTH EF_FACE EF_EYE
            #pragma shader_feature_local _ EF_NORMAL_MAP
            #pragma shader_feature_local _ EF_SOURCE_CHARACTER
            #pragma shader_feature_local _ EF_SOURCE_VIEW_TINT
            #pragma shader_feature_local _ EF_SOURCE_COVERAGE
            #pragma shader_feature_local _ EF_SOURCE_PACKED_MASK
            #pragma shader_feature_local _ EF_SOURCE_COLOR_LUT
            #pragma shader_feature_local _ EF_SOURCE_ANISOTROPIC
            #pragma shader_feature_local _ EF_SOURCE_ENVIRONMENT_REFLECTION
            #pragma shader_feature_local _ EF_SOURCE_SKIN
            #pragma shader_feature_local _ EF_SOURCE_PARALLAX_GLOW
            #include "Library/SourceCharacterLighting.hlsl"
            float4 Fragment(EFVaryings input, bool frontFace : SV_IsFrontFace) : SV_Target
            {
                #if defined(EF_SOURCE_CHARACTER)
                    return float4(EFEvaluateSourceCharacter(input, frontFace), 1);
                #else
                    clip(-1);
                    return 0;
                #endif
            }
            ENDHLSL
        }
        Pass
        {
            Name "Effect"
            Tags { "LightMode"="EndfieldEffect" }
            Cull [_Cull] Blend [_SrcBlend] [_DstBlend] ZWrite [_ZWrite] ZTest LEqual
            HLSLPROGRAM
            #pragma vertex EFVertex
            #pragma fragment Fragment
            #pragma shader_feature_local _ EF_SOURCE_EFFECT
            #include "Library/SourceEffect.hlsl"
            float4 Fragment(EFVaryings input) : SV_Target
            {
                #if defined(EF_SOURCE_EFFECT)
                    return EFSourceEffect(input);
                #else
                    clip(-1);
                    return 0;
                #endif
            }
            ENDHLSL
        }
        Pass
        {
            Name "Outline"
            Tags { "LightMode"="EndfieldOutline" }
            Cull Front ZWrite On ZTest LEqual
            HLSLPROGRAM
            #pragma vertex OutlineVertex
            #pragma fragment Fragment
            EFVaryings OutlineVertex(EFAttributes input)
            {
                EFVaryings o = EFVertex(input);
                o.positionWS += o.normalWS * _OutlineWidth;
                o.positionCS = EFClipPosition(o.positionWS);
                return o;
            }
            EFGBufferOutput Fragment(EFVaryings input)
            {
                clip(_OutlineWidth - 0.000001);
                EFSurface s = (EFSurface)0;
                s.baseColor = 0;
                s.emission = _OutlineColor.rgb;
                s.normalWS = normalize(input.normalWS);
                s.roughness = 1;
                return EFEncodeGBuffer(s, 0);
            }
            ENDHLSL
        }
        Pass
        {
            Name "SurfaceOutline"
            Tags { "LightMode"="EndfieldSurfaceOutline" }
            Stencil { Ref 0 ReadMask 16 WriteMask 0 Comp Equal Pass Keep }
            Cull Front ZWrite On ZTest LEqual
            HLSLPROGRAM
            #pragma vertex EFSourceOutlineVertex
            #pragma fragment EFSourceOutlineFragment
            #pragma shader_feature_local _ EF_SOURCE_SCREEN_OUTLINE
            #include "Library/SourceOutline.hlsl"
            ENDHLSL
        }
        Pass
        {
            Name "MotionVectors"
            Tags { "LightMode"="EndfieldMotionVectors" }
            Cull [_Cull] ZWrite Off ZTest Equal
            HLSLPROGRAM
            #pragma vertex EFMotionVertex
            #pragma fragment EFMotionFragment
            #pragma shader_feature_local _ EF_ALPHA_CLIP
            #pragma shader_feature_local _ EF_SOURCE_COVERAGE
            #include "Library/MotionVectors.hlsl"
            ENDHLSL
        }
        Pass
        {
            Name "CharacterShadowCaster"
            Tags { "LightMode"="CharacterShadowCaster" }
            Cull Off ZWrite On ZTest LEqual ColorMask 0
            HLSLPROGRAM
            #pragma vertex CharacterShadowVertex
            #pragma fragment CharacterShadowFragment
            #pragma shader_feature_local _ EF_ALPHA_CLIP
            #pragma shader_feature_local _ EF_SOURCE_COVERAGE
            #pragma shader_feature_local _ EF_SOURCE_STOCHASTIC_SHADOW
            #include "Library/StochasticCoverage.hlsl"
            struct CharacterShadowAttributes { float3 positionOS : POSITION; float2 uv : TEXCOORD0; };
            struct CharacterShadowVaryings { float4 positionCS : SV_POSITION; float2 uv : TEXCOORD0; };
            CharacterShadowVaryings CharacterShadowVertex(CharacterShadowAttributes input)
            {
                CharacterShadowVaryings output;
                output.positionCS = EFClipPosition(EFWorldPosition(input.positionOS));
                #if UNITY_REVERSED_Z
                    output.positionCS.z = min(output.positionCS.z, output.positionCS.w * UNITY_NEAR_CLIP_VALUE);
                #else
                    output.positionCS.z = max(output.positionCS.z, output.positionCS.w * UNITY_NEAR_CLIP_VALUE);
                #endif
                output.uv = input.uv * _BaseMap_ST.xy + _BaseMap_ST.zw;
                return output;
            }
            float4 CharacterShadowFragment(CharacterShadowVaryings input) : SV_Target
            {
                #if defined(EF_ALPHA_CLIP)
                    clip(SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv).a * _BaseColor.a - _Cutoff);
                #endif
                #if defined(EF_SOURCE_COVERAGE)
                    clip(SAMPLE_TEXTURE2D_BIAS(_CoverageMap, sampler_CoverageMap, input.uv, _SourceMipBias).r - _Cutoff);
                #endif
                #if defined(EF_SOURCE_STOCHASTIC_SHADOW)
                    EFStochasticCoverageClip(TEXTURE2D_ARGS(_AlphaMap,sampler_AlphaMap),input.uv,input.positionCS.xy,_Opacity,_SourceMipBias);
                #endif
                return 0;
            }
            ENDHLSL
        }
        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode"="ShadowCaster" }
            Cull [_Cull] ZWrite On ZTest LEqual ColorMask 0
            HLSLPROGRAM
            #pragma vertex ShadowVertex
            #pragma fragment Fragment
            #pragma shader_feature_local _ EF_ALPHA_CLIP
            #pragma shader_feature_local _ EF_SOURCE_COVERAGE
            #pragma shader_feature_local _ EF_SOURCE_STOCHASTIC_SHADOW
            #include "Library/StochasticCoverage.hlsl"
            float4 _ShadowBias;
            float4 _ShadowLightDirection;
            float4 _ShadowLightPosition;
            float _ShadowLightType;
            EFVaryings ShadowVertex(EFAttributes input)
            {
                EFVaryings o = EFVertex(input);
                float3 lightDirection = _ShadowLightType > .5 ? normalize(_ShadowLightPosition.xyz - o.positionWS) : _ShadowLightDirection.xyz;
                float normalBias = _ShadowBias.y * (1 - saturate(dot(o.normalWS, lightDirection)));
                o.positionWS += o.normalWS * normalBias + lightDirection * _ShadowBias.x;
                o.positionCS = EFClipPosition(o.positionWS);
                #if UNITY_REVERSED_Z
                    o.positionCS.z = min(o.positionCS.z, o.positionCS.w * UNITY_NEAR_CLIP_VALUE);
                #else
                    o.positionCS.z = max(o.positionCS.z, o.positionCS.w * UNITY_NEAR_CLIP_VALUE);
                #endif
                return o;
            }
            float4 Fragment(EFVaryings input) : SV_Target
            {
                #if defined(EF_ALPHA_CLIP)
                    clip(SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, input.uv).a * _BaseColor.a - _Cutoff);
                #endif
                #if defined(EF_SOURCE_COVERAGE)
                    clip(SAMPLE_TEXTURE2D(_CoverageMap, sampler_CoverageMap, input.uv).r - _Cutoff);
                #endif
                #if defined(EF_SOURCE_STOCHASTIC_SHADOW)
                    EFStochasticCoverageClip(TEXTURE2D_ARGS(_AlphaMap,sampler_AlphaMap),input.uv,input.positionCS.xy,_Opacity,_SourceMipBias);
                #endif
                return 0;
            }
            ENDHLSL
        }
    }
    CustomEditor "Endfield.Editor.EndfieldLitShaderGUI"
}
