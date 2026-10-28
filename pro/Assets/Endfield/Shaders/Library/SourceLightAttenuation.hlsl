#ifndef ENDFIELD_SOURCE_LIGHT_ATTENUATION_INCLUDED
#define ENDFIELD_SOURCE_LIGHT_ATTENUATION_INCLUDED

// 原游戏 LocalLighting 的有限能量衰减。位置、颜色、范围仍来自当前 Unity Light；
// 只保留材质受光公式中的 (d² + 1)，避免近距离灯光因标准 1/d² 被放大数百倍。
// invRangeSquared 由管线按 Unity Light.range 计算，不保存截帧灯光常量。
float EFSourceDistanceAttenuation(float distanceSquared, float invRangeSquared)
{
    float normalizedDistanceSquared = distanceSquared * invRangeSquared;
    float cutoff = saturate(1 - normalizedDistanceSquared * normalizedDistanceSquared);
    return cutoff * cutoff / (distanceSquared + 1);
}

#endif
