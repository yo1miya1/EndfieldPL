Shader "Endfield/LayeredEffect"
{
    Properties
    {
        _ColorMask("颜色写入通道",Float)=15
        _BaseMap("主层静态纹理",2D)="white"{}
        _SkyMap("静态环境Cube",Cube)="white"{}
        _BaseColor("主层颜色",Color)=(1,1,1,1)
        _UVTransform("UV缩放偏移",Vector)=(1,1,0,0)
        _UVRotation("UV二维旋转",Vector)=(1,0,0,1)
        _UVVelocity("UV时间与顶点相位速度",Vector)=(0,0,0,0)
        _UVWeights("UV流权重",Vector)=(1,0,0,0)
        _DepthRanges("近远淡出范围",Vector)=(.001,10,120,100)
        _DissolveProfile("溶解边界响应",Vector)=(0,0,0,0)
        _DissolveColor("溶解边缘颜色",Color)=(0,0,0,0)
        _ColorResponse("颜色与饱和度响应",Vector)=(1,1,1,1)
        _SkyRotation("天空水平旋转",Vector)=(1,0,0,1)
        _ShadowTint("阴影乘法色与强度",Color)=(0,0,0,1)
        _SecondaryShadowTint("第二可见性颜色",Color)=(0,0,0,0)
        _ShadowRange("阴影距离混合",Vector)=(0,0,0,0)
        _ShadowOrigin("阴影距离中心",Vector)=(0,0,0,0)
        [Enum(Texture,0,AnimatedLayer,1,Ribbon,2,ViewFilter,3,DepthOnly,4,RadianceSky,5,ShadowMultiplier,6,MotionUv,7)] _Model("功能模型",Float)=0
        _IgnoreVertexColor("忽略顶点色",Float)=0
        _ColorGain("颜色增益",Float)=1
        _AlphaGain("覆盖率增益",Float)=1
        _MonochromeWeight("单色通道混合",Float)=0
        _MipBias("源采样Mip偏移",Float)=0
        _Opacity("整体覆盖率",Float)=1
        _Cutoff("覆盖率裁剪",Float)=0
        _BloomThreshold("高亮增强阈值",Float)=0
        _BloomBoost("高亮增强强度",Float)=0
        _PreExposureWeight("预曝光混合",Float)=0
        _DepthFadeEnabled("深度淡出开关",Float)=0
        _DissolveEnabled("溶解开关",Float)=0
        _DissolveMask("溶解遮罩",Float)=0
        _DissolveHeight("溶解高度影响",Float)=0
        _ResponseWeight("颜色响应混合",Float)=0
        _AlphaMode("覆盖率合成模式",Float)=0
        _InvisibleWeight("隐藏混合",Float)=0
        _UVStreamBlend("替代UV流混合",Float)=0
        _Phase("动画相位",Float)=0
        _PhaseSpeed("相位时钟速度",Float)=0
        _ViewOffset("视图偏移距离",Float)=0
        _ViewOffsetWeight("视图偏移权重",Float)=1
        _RibbonWidth("飘带屏幕宽度",Float)=0
        _ForceNearPlane("强制近深度",Float)=0
        _FilterInfluence("滤层叠色强度",Float)=0
        _FilterOpacity("滤层覆盖率",Float)=1
        _FilterRejectMaterialTag("按GBuffer材质标记屏蔽滤层",Float)=0
        _Cull("Cull",Float)=2
        _ZWrite("ZWrite",Float)=0
        _ZTest("ZTest",Float)=4
        _SrcBlend("SrcBlend",Float)=1
        _DstBlend("DstBlend",Float)=0
        _SrcBlendAlpha("SrcBlendAlpha",Float)=1
        _DstBlendAlpha("DstBlendAlpha",Float)=0
        _BlendOp("BlendOp",Float)=0
        _BlendOpAlpha("BlendOpAlpha",Float)=0
        _StencilRef("StencilRef",Float)=0
        _StencilReadMask("StencilReadMask",Float)=255
        _StencilWriteMask("StencilWriteMask",Float)=255
        _StencilComp("StencilComp",Float)=8
        _StencilPass("StencilPass",Float)=0
        _StencilFail("StencilFail",Float)=0
        _StencilZFail("StencilZFail",Float)=0
    }
    SubShader
    {
        Tags { "RenderPipeline"="EndfieldPipeline" }
        HLSLINCLUDE
        #pragma target 4.5
        #include "Library/LayeredEffects.hlsl"
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
            #pragma vertex EFLayerVertex
            #pragma fragment EFLayerFragment
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
            #pragma vertex EFLayerVertex
            #pragma fragment EFLayerFragment
            ENDHLSL
        }
    }
}
