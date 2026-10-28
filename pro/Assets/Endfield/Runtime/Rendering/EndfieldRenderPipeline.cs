using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace Endfield.Rendering
{
    // 这里只管理相机、剔除与管线寿命；具体画什么交给 Renderer。
    public sealed class EndfieldRenderPipeline : RenderPipeline
    {
        readonly EndfieldRenderPipelineAsset settings;
        readonly EndfieldScriptableRenderer renderer;
        readonly Dictionary<Camera, VolumeStack> cameraVolumes = new Dictionary<Camera, VolumeStack>();
        readonly List<Camera> deadCameras = new List<Camera>();
        readonly bool previousBatcher;
        readonly bool previousLinearLightIntensity;
        readonly bool previousColorTemperature;
        readonly bool previousMotionVectors;
        readonly bool ownsVolumeManager;

        public EndfieldRenderPipeline(EndfieldRenderPipelineAsset settings)
        {
            this.settings = settings;
            previousBatcher = GraphicsSettings.useScriptableRenderPipelineBatching;
            previousLinearLightIntensity = GraphicsSettings.lightsUseLinearIntensity;
            previousColorTemperature = GraphicsSettings.lightsUseColorTemperature;
            previousMotionVectors = SupportedRenderingFeatures.active.motionVectors;
            SupportedRenderingFeatures.active.motionVectors = true;
            GraphicsSettings.useScriptableRenderPipelineBatching = settings.enableSrpBatcher;
            GraphicsSettings.lightsUseLinearIntensity = true;
            GraphicsSettings.lightsUseColorTemperature = true;
            ownsVolumeManager = !VolumeManager.instance.isInitialized;
            if (ownsVolumeManager) VolumeManager.instance.Initialize(settings.defaultVolumeProfile);
            renderer = new EndfieldScriptableRenderer(settings);
        }

        protected override void Render(ScriptableRenderContext context, List<Camera> cameras)
        {
            BeginContextRendering(context, cameras);
            cameras.Sort((left, right) => left.depth.CompareTo(right.depth));
            foreach (Camera camera in cameras)
            {
                if (!camera) continue;
                DepthTextureMode previousDepthMode = camera.depthTextureMode;
                if (settings.enableTemporalAA) camera.depthTextureMode |= DepthTextureMode.Depth | DepthTextureMode.MotionVectors;
                if (!camera.TryGetCullingParameters(out ScriptableCullingParameters parameters))
                {
                    camera.depthTextureMode = previousDepthMode;
                    continue;
                }
                BeginCameraRendering(context, camera);
                try
                {
#if UNITY_EDITOR
                    if (camera.cameraType == CameraType.SceneView) ScriptableRenderContext.EmitWorldGeometryForSceneView(camera);
#endif
                    parameters.shadowDistance = Mathf.Min(settings.shadowDistance, camera.farClipPlane);
                    CullingResults culling = context.Cull(ref parameters);
                    camera.TryGetComponent(out EndfieldCameraSettings cameraSettings);
                    if (!cameraVolumes.TryGetValue(camera, out VolumeStack stack))
                    {
                        stack = VolumeManager.instance.CreateStack();
                        cameraVolumes.Add(camera, stack);
                    }
                    VolumeManager.instance.Update(stack,
                        cameraSettings && cameraSettings.volumeTrigger ? cameraSettings.volumeTrigger : camera.transform,
                        cameraSettings ? cameraSettings.volumeLayerMask : (LayerMask)~0);
                    renderer.Render(context, camera, culling, cameraSettings, stack);
                }
                finally
                {
                    EndCameraRendering(context, camera);
                    context.Submit();
                    camera.depthTextureMode = previousDepthMode;
                }
            }
            deadCameras.Clear();
            foreach (var entry in cameraVolumes) if (!entry.Key) deadCameras.Add(entry.Key);
            foreach (Camera camera in deadCameras)
            {
                VolumeManager.instance.DestroyStack(cameraVolumes[camera]);
                cameraVolumes.Remove(camera);
            }
            EndContextRendering(context, cameras);
        }

        protected override void Dispose(bool disposing)
        {
            renderer.Dispose();
            foreach (VolumeStack stack in cameraVolumes.Values) VolumeManager.instance.DestroyStack(stack);
            cameraVolumes.Clear();
            if (ownsVolumeManager && VolumeManager.instance.isInitialized) VolumeManager.instance.Deinitialize();
            GraphicsSettings.useScriptableRenderPipelineBatching = previousBatcher;
            GraphicsSettings.lightsUseLinearIntensity = previousLinearLightIntensity;
            GraphicsSettings.lightsUseColorTemperature = previousColorTemperature;
            SupportedRenderingFeatures.active.motionVectors = previousMotionVectors;
            base.Dispose(disposing);
        }
    }
}
