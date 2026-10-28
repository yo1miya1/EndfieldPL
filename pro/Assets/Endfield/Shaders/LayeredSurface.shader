Shader "Endfield/LayeredSurface"
{
    Properties
    {
        _ColorMask("颜色写入通道",Float)=15
        _LayerResponseMap("可选叶颜色/裁剪遮罩",2D)="white"{}
        _LayerIndirectRange("遮罩颜色响应范围",Vector)=(1,1,0,0)
        _LayerIndirectTint("遮罩颜色响应",Color)=(1,1,1,1)
        _LayerTintUv("平面遮罩UV",Vector)=(1,1,0,0)
        _LayerTintColor("平面边缘颜色",Color)=(0,0,0,1)
        _LayerTintAxis("世界平面轴",Vector)=(0,1,0,0)
        _LayerTintResponse("平面混合与边缘响应",Vector)=(0,1,0,0)
        _LayerTintControls("平面遮罩控制",Vector)=(0,0,0,0)
        _LayerObjectOrigin("平面局部原点",Vector)=(0,0,0,0)
        _LayerInstanceCut("实例裁剪阈值",Float)=0

        _RenderPassMask ("渲染Pass位掩码（0自动）", Float) = 0
        [Toggle(EF_SOURCE_INDIRECT_COLOR)] _SourceIndirectColor ("源间接基础色增益与饱和", Float) = 0
        [Toggle(EF_SOURCE_GROUND)] _SourceGround ("源台面GBuffer模型", Float) = 0
        _GroundPatternColor ("台面图案颜色与混合强度", Vector) = (1,1,1,0)
        _GroundPatternUV_ST ("台面图案UV变换", Vector) = (1,1,0,0)
        _GroundBaseUV_ST ("台面底图UV变换", Vector) = (1,1,0,0)
        _GroundCoverageParameters ("台面覆盖/响应/运动掩码", Vector) = (0,1,1,1)
        _GroundDistanceParameters ("台面近远区间/运动缩放", Vector) = (30,14,0,0)
        _GroundColorGain ("台面环境混合/底图增益/初始帧亮度", Vector) = (0,1,1,0)
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
        _OutlineStencilReadMask ("模板读取位掩码", Float) = 16
        _OutlineStencilWriteMask ("模板写入位掩码", Float) = 16
        [Enum(UnityEngine.Rendering.StencilOp)] _StencilPass ("模板通过操作", Float) = 2
        [Enum(UnityEngine.Rendering.StencilOp)] _StencilFail ("模板失败操作", Float) = 0
        [Enum(UnityEngine.Rendering.StencilOp)] _StencilZFail ("模板深度失败操作", Float) = 0
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
        _SourceDirectTint ("主光材质色响应", Color) = (1,1,1,1)
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
        _ShadowCoverageMode ("投影覆盖率模式", Float) = 0
            _ZTest("ZTest",Float)=4
        _SrcBlendAlpha("SrcBlendAlpha",Float)=1
        _DstBlendAlpha("DstBlendAlpha",Float)=0
        _BlendOp("BlendOp",Float)=0
        _BlendOpAlpha("BlendOpAlpha",Float)=0
        _StencilRef("StencilRef",Float)=0
        _StencilReadMask("StencilReadMask",Float)=255
        _StencilWriteMask("StencilWriteMask",Float)=255
        _StencilComp("StencilComp",Float)=8
}
    SubShader
    {
        Tags { "RenderPipeline"="EndfieldPipeline" }
        HLSLINCLUDE
        #pragma target 4.5
        #define EF_CLOTH 1
        #include "Library/LayeredSurface.hlsl"
        ENDHLSL
        Pass
        {
            Name "EndfieldEffect"
            Tags { "LightMode"="EndfieldEffect" }
            ColorMask [_ColorMask]
            Cull [_Cull] ZWrite [_ZWrite] ZTest [_ZTest]
            Blend [_SrcBlend] [_DstBlend], [_SrcBlendAlpha] [_DstBlendAlpha]
            BlendOp [_BlendOp], [_BlendOpAlpha]
            Stencil { Ref [_StencilRef] ReadMask [_StencilReadMask] WriteMask [_StencilWriteMask] Comp [_StencilComp] Pass [_StencilPass] Fail [_StencilFail] ZFail [_StencilZFail] }
            HLSLPROGRAM
            #pragma vertex EFLayeredSurfaceVertex
            #pragma fragment EFLayeredSurfaceFragment
            #pragma shader_feature_local _ EF_SOURCE_CHARACTER
            #pragma shader_feature_local _ EF_NORMAL_MAP
            #pragma shader_feature_local _ EF_SOURCE_COLOR_LUT
            #pragma shader_feature_local _ EF_SOURCE_PACKED_MASK
            #pragma shader_feature_local _ EF_SOURCE_ENVIRONMENT_REFLECTION
            #pragma shader_feature_local _ EF_SOURCE_VIEW_TINT
            #pragma shader_feature_local _ EF_SOURCE_COVERAGE
            #pragma shader_feature_local _ EF_LAYER_MASKED_INDIRECT
            #pragma shader_feature_local _ EF_LAYER_UV1_TINT
            #pragma shader_feature_local _ EF_LAYER_OUTLINE
            #pragma shader_feature_local _ EF_LAYER_COLOR_OVERRIDE
            #pragma shader_feature_local _ EF_LAYER_INDIRECT_RESPONSE
            #pragma shader_feature_local _ EF_LAYER_PREMULTIPLIED
            #pragma shader_feature_local _ EF_LAYER_ALPHA_CLIP
            ENDHLSL
        }
        Pass
        {
            Name "EndfieldForward"
            Tags { "LightMode"="EndfieldForward" }
            ColorMask [_ColorMask]
            Cull [_Cull] ZWrite [_ZWrite] ZTest [_ZTest]
            Blend [_SrcBlend] [_DstBlend], [_SrcBlendAlpha] [_DstBlendAlpha]
            BlendOp [_BlendOp], [_BlendOpAlpha]
            Stencil { Ref [_StencilRef] ReadMask [_StencilReadMask] WriteMask [_StencilWriteMask] Comp [_StencilComp] Pass [_StencilPass] Fail [_StencilFail] ZFail [_StencilZFail] }
            HLSLPROGRAM
            #pragma vertex EFLayeredSurfaceVertex
            #pragma fragment EFLayeredSurfaceFragment
            #pragma shader_feature_local _ EF_SOURCE_CHARACTER
            #pragma shader_feature_local _ EF_NORMAL_MAP
            #pragma shader_feature_local _ EF_SOURCE_COLOR_LUT
            #pragma shader_feature_local _ EF_SOURCE_PACKED_MASK
            #pragma shader_feature_local _ EF_SOURCE_ENVIRONMENT_REFLECTION
            #pragma shader_feature_local _ EF_SOURCE_VIEW_TINT
            #pragma shader_feature_local _ EF_SOURCE_COVERAGE
            #pragma shader_feature_local _ EF_LAYER_MASKED_INDIRECT
            #pragma shader_feature_local _ EF_LAYER_UV1_TINT
            #pragma shader_feature_local _ EF_LAYER_OUTLINE
            #pragma shader_feature_local _ EF_LAYER_COLOR_OVERRIDE
            #pragma shader_feature_local _ EF_LAYER_INDIRECT_RESPONSE
            #pragma shader_feature_local _ EF_LAYER_PREMULTIPLIED
            #pragma shader_feature_local _ EF_LAYER_ALPHA_CLIP
            ENDHLSL
        }
        UsePass "Endfield/HybridLit/ShadowCaster"
        UsePass "Endfield/HybridLit/CharacterShadowCaster"
    }
}
