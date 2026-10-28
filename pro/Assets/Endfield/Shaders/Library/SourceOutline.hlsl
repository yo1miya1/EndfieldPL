#ifndef ENDFIELD_SOURCE_OUTLINE_INCLUDED
#define ENDFIELD_SOURCE_OUTLINE_INCLUDED

// 源635:203-214的atan多项式，输入由当前相机投影焦距生成。
float EFSourceOutlineHalfFov()
{
    float inverseFocal = 1/abs(glstate_matrix_projection[1][1]);
    float argument = inverseFocal<1 ? inverseFocal : 1/inverseFocal;
    float square = argument*argument;
    float polynomial = (0.0872929022*square-0.301894993)*square+1;
    float angle = argument*polynomial;
    return inverseFocal<1 ? angle : 1.57079637-angle;
}

EFVaryings EFSourceOutlineVertex(EFAttributes input)
{
    EFVaryings output = EFVertex(input);
    float3 normal = output.normalWS;
    if (_SourceOutlineSmoothNormal > 0.5)
    {
        float2 xy = input.outlineNormalTS;
        float z = sqrt(1-min(dot(xy,xy),1));
        float3 bitangent = cross(output.normalWS,output.tangentWS.xyz)*output.tangentWS.w;
        normal = output.tangentWS.xyz*xy.x+bitangent*xy.y+output.normalWS*z;
    }
    // dest=r6.zw,resource swizzle=zwxy，因此实际宽度R、深度G。
    float2 mask = SAMPLE_TEXTURE2D_LOD(_SourceOutlineWidthMap,sampler_SourceOutlineWidthMap,output.uv,0).rg;
    // 原cb0[32..34]为VP，包含投影焦距；不能误换成只乘View。
    float2 viewNormal = mul(unity_MatrixVP,float4(normal,0)).xy;
    viewNormal *= rsqrt(max(dot(viewNormal,viewNormal),1e-30));
    float halfFov = EFSourceOutlineHalfFov();
    float2 direction = viewNormal*float2(_ScreenParams.y/_ScreenParams.x,1);
    float2 clipOffset = direction*(0.392699033/halfFov)*_SourceOutlineWidth;
    clipOffset *= saturate(output.positionCS.w*halfFov*4.58366251);
    float2 proposed = clipOffset*0.00499999989;
    float depthForMinimum = min(max(output.positionCS.w,0),1.57079613/halfFov);
    float2 minimumOffset = depthForMinimum/_ScreenParams.xy;
    clipOffset = float2(abs(proposed.x)<minimumOffset.x ? sign(clipOffset.x)*minimumOffset.x : proposed.x,
                        abs(proposed.y)<minimumOffset.y ? sign(clipOffset.y)*minimumOffset.y : proposed.y);
    output.positionCS.xy += clipOffset*mask.r;
    // 使用当前Unity GPU投影计算偏移后的NDC深度，同时保留轮廓的clip.w。
    // 源本帧M13.y=0；此形式同时兼容正反Z和透视/正交投影。
    float3 viewPosition = mul(unity_MatrixV,float4(output.positionWS,1)).xyz;
    viewPosition.z -= mask.g*_SourceOutlineDepth*0.1;
    float4 depthClip = mul(glstate_matrix_projection,float4(viewPosition,1));
    output.positionCS.z = depthClip.z/depthClip.w*output.positionCS.w;
    // 抖动直接来自当前Unity VP；不把源frame[19]的捕获抖动硬塞进运行时。
    return output;
}

float4 EFSourceOutlineFragment(EFVaryings input) : SV_Target
{
    clip(SAMPLE_TEXTURE2D_BIAS(_SourceOutlineCoverageMap,sampler_SourceOutlineCoverageMap,input.uv,_SourceMipBias).r-_SourceOutlineCutoff);
    // 源PS只写RT0=(0,0,0,0)，其余附件保留先前表面写入的值。
    return 0;
}
#endif
