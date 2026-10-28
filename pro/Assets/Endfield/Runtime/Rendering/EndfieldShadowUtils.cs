using UnityEngine;
using UnityEngine.Rendering;

namespace Endfield.Rendering
{
    internal static class EndfieldShadowUtils
    {
        public static Matrix4x4 AtlasMatrix(Matrix4x4 projection, Matrix4x4 view, int tile, int columns)
        {
            if (SystemInfo.usesReversedZBuffer)
            {
                projection.m20 = -projection.m20; projection.m21 = -projection.m21;
                projection.m22 = -projection.m22; projection.m23 = -projection.m23;
            }
            Matrix4x4 clipToTexture = Matrix4x4.identity;
            clipToTexture.m00 = clipToTexture.m11 = clipToTexture.m22 = .5f;
            clipToTexture.m03 = clipToTexture.m13 = clipToTexture.m23 = .5f;
            Matrix4x4 atlas = Matrix4x4.identity;
            atlas.m00 = atlas.m11 = 1f / columns;
            atlas.m03 = (tile % columns) / (float)columns;
            atlas.m13 = (tile / columns) / (float)columns;
            return atlas * clipToTexture * projection * view;
        }

        // 本机URP ShadowUtils同样以阴影视锥中点尺寸估算punctual的世界texel。
        public static Vector4 Bias(VisibleLight visible, Matrix4x4 projection, int resolution)
        {
            Light light = visible.light;
            float frustumSize;
            if (visible.lightType == LightType.Directional) frustumSize = 2f / Mathf.Abs(projection.m00);
            else
            {
                float angle = visible.lightType == LightType.Point
                    ? 90 + PointGuardAngle(resolution, light.shadows == LightShadows.Soft) : visible.spotAngle;
                frustumSize = Mathf.Tan(angle * .5f * Mathf.Deg2Rad) * visible.range;
            }
            float kernelRadius = light.shadows == LightShadows.Soft ? 2.5f : 1f;
            float texelSize = frustumSize / resolution * kernelRadius;
            return new Vector4(-light.shadowBias * texelSize,
                visible.lightType == LightType.Point ? 0 : -light.shadowNormalBias * texelSize, 0, 0);
        }

        // 沿用URP点光六面接缝保护角表，软阴影再为5x5过滤扩大视锥。
        public static float PointGuardAngle(int resolution, bool soft)
        {
            float angle = resolution <= 16 ? 43f : resolution <= 32 ? 18.55f : resolution <= 64 ? 8.63f
                : resolution <= 128 ? 4.13f : resolution <= 256 ? 2.03f : resolution <= 512 ? 1f
                : resolution <= 1024 ? .5f : .25f;
            if (soft) angle += resolution <= 32 ? 9.35f : resolution <= 64 ? 4.07f : resolution <= 128 ? 1.77f
                : resolution <= 256 ? .85f : resolution <= 512 ? .39f : resolution <= 1024 ? .17f : .074f;
            return angle;
        }

        public static void SetCasterGlobals(CommandBuffer command, VisibleLight visible, Matrix4x4 projection, int resolution)
        {
            command.SetGlobalVector("_ShadowBias", Bias(visible, projection, resolution));
            command.SetGlobalVector("_ShadowLightDirection", -visible.localToWorldMatrix.GetColumn(2));
            command.SetGlobalVector("_ShadowLightPosition", visible.localToWorldMatrix.GetColumn(3));
            command.SetGlobalFloat("_ShadowLightType", visible.lightType == LightType.Directional ? 0 : 1);
        }
    }
}
