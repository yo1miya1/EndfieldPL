using System;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace Endfield.Rendering
{
    // 持久图像只归一个Camera所有；相机结束释放临时RT，历史在相机删除或管线销毁时释放。
    internal sealed class EndfieldCameraHistory : IDisposable
    {
        public RenderTexture color;
        public Matrix4x4 previousNonJitteredViewProjection;
        public bool valid;
        int sampleIndex, resetVersion;
        Matrix4x4 previousProjection;
        Matrix4x4 lastView;
        int settledFrames;
        public bool NeedsWarmup => settledFrames < 16;

        public Matrix4x4 Begin(Camera camera, int width, int height, int requestedResetVersion)
        {
            if (!color || color.width != width || color.height != height)
            {
                Dispose();
                color = new RenderTexture(new RenderTextureDescriptor(width, height)
                {
                    graphicsFormat = GraphicsFormat.R16G16B16A16_SFloat,
                    depthStencilFormat = GraphicsFormat.None, msaaSamples = 1
                }) { name = camera.name + " Temporal history", filterMode = FilterMode.Bilinear, wrapMode = TextureWrapMode.Clamp, hideFlags = HideFlags.HideAndDontSave };
                color.Create();
            }
            Matrix4x4 projection = camera.projectionMatrix;
            if (resetVersion != requestedResetVersion || projection != previousProjection) valid = false;
            if (!valid) sampleIndex = 0;
            if (!valid || lastView != camera.worldToCameraMatrix) settledFrames = 0;
            lastView = camera.worldToCameraMatrix;
            resetVersion = requestedResetVersion;
            previousProjection = projection;
            // 与Unity TemporalAA一致的Halton(2,3)，按实际Camera.Render次数推进，离屏预热也能积累。
            int index = (sampleIndex & 1023) + 1;
            float x = HaltonSequence.Get(index, 2) - .5f;
            float y = HaltonSequence.Get(index, 3) - .5f;
            return Matrix4x4.Translate(new Vector3(2 * x / width, 2 * y / height, 0)) * projection;
        }

        public void Commit(Matrix4x4 nonJitteredViewProjection)
        {
            previousNonJitteredViewProjection = nonJitteredViewProjection;
            sampleIndex++;
            settledFrames++;
            valid = true;
        }

        public void Dispose()
        {
            if (color) { color.Release(); CoreUtils.Destroy(color); }
            color = null;
            valid = false;
            sampleIndex = 0;
        }
    }
}
