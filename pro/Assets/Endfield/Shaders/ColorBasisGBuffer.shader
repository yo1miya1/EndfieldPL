Shader "Endfield/ColorBasisGBuffer"
{
    Properties
    {
        _BaseMap ("基础颜色",2D)="white" {}
        _SourceMipBias ("源Mip偏移",Float)=0
        _ColorBasisNoiseMap ("扭曲噪声",2D)="gray" {}
        _ColorBasisCoverage ("UV选择/顶点色反转/增益",Vector)=(1,0,1,0)
        _ColorBasisTint ("基础乘色",Color)=(1,1,1,1)
        _ColorBasisResponse ("扭曲强度/底图反转",Vector)=(0,0,0,0)
        _ColorBasisColorParams ("保留的颜色参数",Vector)=(0,0,0,0)
        _ColorBasisVelocity ("基础与噪声UV速度",Vector)=(0,0,0,0)
        _ColorBasisRotation ("基础UV旋转矩阵",Vector)=(1,0,0,1)
        _ColorBasisUVWeights ("基础UV0/UV1混合",Vector)=(1,0,0,0)
        _ColorBasisBaseUV_ST ("基础UV变换",Vector)=(1,1,0,0)
        _ColorBasisDistortion ("噪声重映射/解码选择/幅度XY",Vector)=(0,1,1,1)
        _ColorBasisNoiseUV_ST ("噪声UV变换",Vector)=(1,1,0,0)
        _ColorBasisNoiseRotation ("噪声UV旋转矩阵",Vector)=(1,0,0,1)
        _ColorBasisNoiseWeights ("噪声UV0/UV1混合",Vector)=(1,0,0,0)
        _ColorBasisSurface ("漫反分配/金属/粗糙/受光",Vector)=(0,0,1,0)
        _ColorBasisExposure ("源预曝光乘数",Float)=1
        _ColorBasisPhase ("UV动画相位",Float)=0
        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("剔除",Float)=0
        _ZWrite ("深度写入",Float)=1
        _OutlineStencilReference ("模板参考",Float)=0
        _OutlineStencilReadMask ("模板读掩码",Float)=255
        _OutlineStencilWriteMask ("模板写掩码",Float)=255
        _OutlineStencilComparison ("模板比较",Float)=8
        _StencilPass ("模板通过操作",Float)=0
        _StencilFail ("模板失败操作",Float)=0
        _StencilZFail ("深度失败模板操作",Float)=0
    }
    SubShader
    {
        Tags {"RenderPipeline"="EndfieldPipeline" "RenderType"="Opaque"}
        Pass
        {
            Name "GBuffer"
            Tags {"LightMode"="EndfieldGBuffer"}
            Cull [_Cull] ZWrite [_ZWrite] ZTest LEqual
            Stencil {Ref [_OutlineStencilReference] ReadMask [_OutlineStencilReadMask] WriteMask [_OutlineStencilWriteMask] Comp [_OutlineStencilComparison] Pass [_StencilPass] Fail [_StencilFail] ZFail [_StencilZFail]}
            HLSLPROGRAM
            #pragma target 4.5
            #pragma vertex Vertex
            #pragma fragment Fragment
            #include "Library/Coordinates.hlsl"
            #include "Library/GBuffer.hlsl"
            TEXTURE2D(_BaseMap);SAMPLER(sampler_BaseMap);
            TEXTURE2D(_ColorBasisNoiseMap);SAMPLER(sampler_ColorBasisNoiseMap);
            CBUFFER_START(UnityPerMaterial)
            float4 _ColorBasisCoverage,_ColorBasisTint,_ColorBasisResponse,_ColorBasisColorParams;
            float4 _ColorBasisVelocity,_ColorBasisRotation,_ColorBasisUVWeights,_ColorBasisBaseUV_ST;
            float4 _ColorBasisDistortion,_ColorBasisNoiseUV_ST,_ColorBasisNoiseRotation,_ColorBasisNoiseWeights;
            float4 _ColorBasisSurface;
            float _SourceMipBias,_ColorBasisExposure,_ColorBasisPhase;
            CBUFFER_END
            struct Attributes {float3 positionOS:POSITION;float3 normalOS:NORMAL;float4 extra0:TEXCOORD3;float4 extra1:TEXCOORD4;float4 color:COLOR;};
            struct Varyings {float4 positionCS:SV_POSITION;float3 normalWS:TEXCOORD0;float4 uv:TEXCOORD1;float4 color:COLOR;};
            Varyings Vertex(Attributes i)
            {
                Varyings o;o.positionCS=EFClipPosition(EFWorldPosition(i.positionOS));o.normalWS=EFWorldNormal(i.normalOS);
                o.uv=float4(i.extra0.xy,lerp(i.extra1.xy,i.extra0.zw,_ColorBasisCoverage.x));o.color=i.color;return o;
            }
            float2 RotateUV(float2 uv,float4 rotation) {return float2(dot(uv-.5,rotation.xz),dot(uv-.5,rotation.yw))+.5;}
            EFGBufferOutput Fragment(Varyings i,bool frontFace:SV_IsFrontFace)
            {
                // GBufferSurface/Graph06：保留两套独立UV、原噪声解码与顶点乘色。
                float2 baseUV=i.uv.xy*_ColorBasisUVWeights.x+i.uv.zw*_ColorBasisUVWeights.y;
                baseUV+=_ColorBasisPhase*_ColorBasisVelocity.xy+i.uv.z*_ColorBasisVelocity.zw;
                baseUV=RotateUV(baseUV,_ColorBasisRotation)*_ColorBasisBaseUV_ST.xy+_ColorBasisBaseUV_ST.zw;
                float2 noiseUV=i.uv.xy*_ColorBasisNoiseWeights.x+i.uv.zw*_ColorBasisNoiseWeights.y;
                noiseUV+=_ColorBasisPhase*_ColorBasisVelocity.xy+i.uv.z*_ColorBasisVelocity.zw;
                noiseUV=RotateUV(noiseUV,_ColorBasisNoiseRotation)*_ColorBasisNoiseUV_ST.xy+_ColorBasisNoiseUV_ST.zw;
                float4 noise=SAMPLE_TEXTURE2D_BIAS(_ColorBasisNoiseMap,sampler_ColorBasisNoiseMap,noiseUV,_SourceMipBias);
                float noiseR=noise.r*(1+_ColorBasisDistortion.x)-_ColorBasisDistortion.x;
                float2 distortion=_ColorBasisDistortion.y!=0 ? (float2(noiseR*noise.a,noise.g)*2-1)*_ColorBasisDistortion.z : noiseR*_ColorBasisDistortion.zw;
                float3 base=SAMPLE_TEXTURE2D_BIAS(_BaseMap,sampler_BaseMap,baseUV+distortion*_ColorBasisResponse.x,_SourceMipBias).rgb;
                base=lerp(base,1-base,_ColorBasisResponse.y);
                float3 color=base*lerp(i.color.rgb,1-i.color.rgb,_ColorBasisCoverage.y)*_ColorBasisTint.rgb*_ColorBasisCoverage.z;
                color=clamp(color*_ColorBasisExposure,0,1000);
                EFGBufferOutput o;o.target0=float4(color*(1-_ColorBasisSurface.x),.5);
                o.target1=float4(.5,.5,_ColorBasisSurface.w,0);o.target2=float4(_ColorBasisSurface.y,1,0,0);
                o.target3=float4(EFEncodeNormal(normalize(i.normalWS)*(frontFace?1:-1)),_ColorBasisSurface.z,0);
                o.target4=float4(color*_ColorBasisSurface.x,0);return o;
            }
            ENDHLSL
        }
    }
}
