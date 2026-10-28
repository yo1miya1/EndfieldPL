#ifndef ENDFIELD_CHARACTER_SHADOWS_INCLUDED
#define ENDFIELD_CHARACTER_SHADOWS_INCLUDED
#include "Shadows.hlsl"

// 运行时每相机由CharacterShadowProvider生成；矩阵来自Unity实时Light与组包围体。
// 参数依次为strength / worldTexelX / depthBiasTexels / normalBiasTexels。
TEXTURE2D(_CharacterShadowmapTexture);
SAMPLER(sampler_CharacterShadowmapTexture);
float4x4 _CharacterWorldToShadow[16];
float4 _CharacterShadowRects[16];
float4 _CharacterShadowParams[16];
float4 _CharacterShadowFilterRadii[16];
float4 _CharacterShadowLightDirections[16];
float4 _CharacterShadowAtlasSize;
int _CharacterShadowCount;

// 保留原10/10/10/2的GB2载体与角色one-hot位布局；角色0仍写原捕获的258。
// 8..23为最多16个角色；其余位原样保留，不拿RT格式通道另作actor整数。
float4 EFCharacterShadowPayload(float4 payload, int characterIndex)
{
    uint4 fields = (uint4)(payload * float4(1023,1023,1023,3) + 0.5);
    uint packed = fields.x | (fields.y << 10) | (fields.z << 20) | (fields.w << 30);
    // 离线捕获的角色ID不参与运行时分组；未注册Renderer必须清actor位，
    // 否则其GBuffer调试会误采当前场景另一个动态组0，而Forward实际回退CSM。
    packed &= 0xFF0000FFu;
    if (characterIndex >= 0 && characterIndex < 16)
        packed |= 1u << (characterIndex + 8);
    return float4(packed & 1023u, (packed >> 10) & 1023u,
        (packed >> 20) & 1023u, packed >> 30) / float4(1023,1023,1023,3);
}

int EFCharacterShadowIndexFromPayload(float4 payload)
{
    uint4 fields = (uint4)(payload * float4(1023,1023,1023,3) + 0.5);
    uint packed = fields.x | (fields.y << 10) | (fields.z << 20) | (fields.w << 30);
    return firstbithigh(packed & 0x00FFFF00u) - 8;
}

// SI1_914 的16组旋转/圆盘常量。直接保留DXBC immediate buffer原位值，
// 避免反编译文本六位小数的舍入；离线证据见character-shadow-kernel.json。
static const uint4 EFCharacterShadowDisk[16] = {
    uint4(0xBECC9FB3u,0x3F6AAA92u,0xBF7127FAu,0xBECC51E0u),
    uint4(0x3DFF004Eu,0xBF7E0201u,0x3F7211EEu,0xBF44D71Bu),
    uint4(0x3F5A33E4u,0x3F05E104u,0xBDC0E398u,0xBF6DEC6Bu),
    uint4(0xBE6AD0E5u,0x3F792DA8u,0x3EB09E84u,0x3E967720u),
    uint4(0xBF45BC68u,0x3F2297D0u,0xBF6A777Eu,0x3EEA5988u),
    uint4(0x3F4AF1D4u,0xBF1C0B0Eu,0xBF50C0D4u,0xBF610E50u),
    uint4(0xBF13FB11u,0x3F50E57Bu,0xBEC3FB24u,0x3E8DB498u),
    uint4(0xBF54C4E9u,0xBF0E5B2Eu,0x3F798F60u,0x3F41A8ECu),
    uint4(0x3F4ECBA4u,0x3F16E719u,0x3EE2EF78u,0xBF79A12Cu),
    uint4(0x3EF15D5Cu,0x3F61C4F0u,0x3F099500u,0xBEF28D4Au),
    uint4(0xBEA0C12Du,0xBF730DF5u,0xBE87AA08u,0xBED67E06u),
    uint4(0xBF71EBF6u,0xBEA7733Bu,0x3F4ABEE2u,0x3E437BC8u),
    uint4(0xBE3D7A72u,0xBF7B944Bu,0xBE77B198u,0x3F7F3FA8u),
    uint4(0xBF6F0AA0u,0x3EB7400Cu,0xBF5068D4u,0x3F6A148Au),
    uint4(0xBF7F63A3u,0x3D8D62E7u,0x3E4CA330u,0x3F495268u),
    uint4(0x3E9CBCC8u,0x3F73B5A5u,0x3E134898u,0xBE106460u)
};

// 源914从GB3解码片元扰动N。outwardLight与Unity towardLight相反。
// 偏移数值用当前独立角色阴影投影的X方向worldTexel换算，非固定世界单位。
float3 EFCharacterShadowReceiverPosition(float3 positionWS, float3 normalWS,
    float3 towardLight, float worldTexelX, float2 receiverBiasTexels)
{
    float3 outwardLight = -towardLight;
    float incidence = 1 - clamp(dot(normalWS, outwardLight), 0, 0.9);
    float2 offsetWorld = receiverBiasTexels * (worldTexelX * incidence);
    return positionWS - outwardLight * offsetWorld.x + normalWS * offsetWorld.y;
}

// 源914的G通道：16个Gather共64个深度值，不是硬比较的PCF平均。
// projectedUVZ与纹理均采用Unity当前阴影矩阵/当前几何生成；没有捕获图输入。
float EFCharacterShadowFilter(TEXTURE2D_PARAM(shadowMap, shadowSampler),
    float3 projectedUVZ, float2 screenPixel, float2 atlasTexelSize, float2 radiusTexels)
{
    uint2 pixel = (uint2)screenPixel;
    uint rotationIndex = ((pixel.x & 3u) << 2u) | (pixel.y & 3u);
    float2 rotation = asfloat(EFCharacterShadowDisk[rotationIndex]).xy;
    float2 flippedRotation = rotation * float2(1, -1);
    // 原式同一个1/sourceAtlasWidth作用于两轴。离线profile保存由此得到的像素半径比，
    // 再按当前图集各轴换算UV。SI1是4/2，Typhon2是4/4，动态打包不改变源采样范围。
    float2 radiusUV = atlasTexelSize * radiusTexels;
    float receiverDepth = projectedUVZ.z;
    #if !UNITY_REVERSED_Z
        receiverDepth = 1 - receiverDepth;
    #endif
    // 源投影有效区间先将receiverZ限制为至少.01，再用于相对深度差归一化。
    receiverDepth = max(receiverDepth, 0.01);
    float blockerCount = 0;
    float positiveDepthSum = 0;
    [unroll] for (int sampleIndex = 0; sampleIndex < 16; sampleIndex++)
    {
        float2 disk = asfloat(EFCharacterShadowDisk[sampleIndex]).zw;
        float2 offset = float2(dot(disk, flippedRotation), dot(disk.yx, rotation));
        float4 depths = GATHER_RED_TEXTURE2D(shadowMap, shadowSampler,
            projectedUVZ.xy + offset * radiusUV);
        #if !UNITY_REVERSED_Z
            depths = 1 - depths;
        #endif
        float4 delta = depths - receiverDepth;
        float4 blockers = step(0, delta);
        blockerCount += dot(blockers, float4(1,1,1,1));
        positiveDepthSum += dot(delta, blockers);
    }
    // 没有阻挡者时源式最终为1；显式处理分母0，不依赖0/0的GPU饱和行为。
    if (blockerCount == 0) return 1;
    float signedCoverage = blockerCount * (1.0 / 32.0) - 1;
    float edgeWeight = 1 - abs(signedCoverage);
    float edgeCubic = edgeWeight * edgeWeight * edgeWeight;
    float relativeSeparation = saturate(positiveDepthSum / (blockerCount * receiverDepth));
    float transition = lerp(edgeCubic, edgeWeight, relativeSeparation);
    // 依据阻挡率的哪一侧恢复可见性；64/64阻挡为0，32/64为.5。
    return min(1, 0.5 - 0.5 * sign(signedCoverage) * (1 - transition));
}

float EFCharacterShadow(float3 positionWS, float3 normalWS, float2 screenPixel, int characterIndex)
{
    // 没有角色组时继续使用普通Unity主光阴影；组件不是渲染角色的必要条件。
    if (characterIndex < 0 || characterIndex >= _CharacterShadowCount)
        return EFMainShadow(positionWS);
    float4 parameters = _CharacterShadowParams[characterIndex];
    if (parameters.x <= 0) return 1;
    float3 receiver = EFCharacterShadowReceiverPosition(positionWS, normalWS,
        _CharacterShadowLightDirections[characterIndex].xyz, parameters.y, parameters.zw);
    float4 projected = mul(_CharacterWorldToShadow[characterIndex], float4(receiver,1));
    float3 coordinates = projected.xyz / projected.w;
    float4 rectangle = _CharacterShadowRects[characterIndex];
    // 对应源914的独立投影域外返回1，不对矩形外采样做边缘复制。
    if (projected.w <= 0 || any(coordinates.xy <= rectangle.xy)
        || any(coordinates.xy >= rectangle.zw) || coordinates.z < 0 || coordinates.z >= 1)
        return 1;
    float visibility = EFCharacterShadowFilter(TEXTURE2D_ARGS(_CharacterShadowmapTexture,
        sampler_CharacterShadowmapTexture), coordinates, screenPixel,
        _CharacterShadowAtlasSize.xy, _CharacterShadowFilterRadii[characterIndex].xy);
    return lerp(1, visibility, parameters.x);
}
#endif
