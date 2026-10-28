using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Rendering;

namespace Endfield.Rendering
{
    // 顺序就在这里。需要加新效果时，加一个小 Pass，而不是恢复截帧事件图。
    public sealed class EndfieldScriptableRenderer : IDisposable
    {
        readonly EndfieldRenderPipelineAsset settings;
        readonly EndfieldRenderPass[] passes;
        readonly Material lightingMaterial, postMaterial, temporalMaterial;
        readonly EndfieldColorLutBuilder colorLutBuilder;
        readonly Dictionary<Camera, EndfieldCameraHistory> histories = new Dictionary<Camera, EndfieldCameraHistory>();
        readonly List<Camera> removedCameras = new List<Camera>();

        public EndfieldScriptableRenderer(EndfieldRenderPipelineAsset settings)
        {
            this.settings = settings;
            Shader lighting = settings.deferredLightingShader ? settings.deferredLightingShader : Shader.Find("Hidden/Endfield/DeferredLighting");
            Shader post = settings.postProcessShader ? settings.postProcessShader : Shader.Find("Hidden/Endfield/PostProcess");
            if (lighting) lightingMaterial = CoreUtils.CreateEngineMaterial(lighting);
            if (post) postMaterial = CoreUtils.CreateEngineMaterial(post);
            Shader temporal = settings.temporalAAShader ? settings.temporalAAShader : Shader.Find("Hidden/Endfield/TemporalAA");
            if (temporal) temporalMaterial = CoreUtils.CreateEngineMaterial(temporal);
            colorLutBuilder = new EndfieldColorLutBuilder(settings.colorLutShader);
            passes = new EndfieldRenderPass[] {
                new EndfieldShadowPass(), new EndfieldOutlinePass(), new EndfieldGBufferPass(),
                new EndfieldLightingPass(), new EndfieldTransparentPass(), new EndfieldPostProcessPass(), new EndfieldUIPass()
            };
        }

        internal void Render(ScriptableRenderContext context, Camera camera, CullingResults culling,
            EndfieldCameraSettings cameraSettings, VolumeStack volumeStack)
        {
            var frame = new EndfieldFrameData {
                context = context, camera = camera, culling = culling, settings = settings,
                cameraSettings = cameraSettings, volumeStack = volumeStack,
                lightingMaterial = lightingMaterial, postMaterial = postMaterial,
                temporalMaterial = temporalMaterial,
                colorLutBuilder = colorLutBuilder,
                command = CommandBufferPool.Get("Endfield: " + camera.name),
                targets = new EndfieldCameraTargets(camera, Mathf.Clamp(settings.renderScale, .25f, 2f)),
                debugView = cameraSettings && cameraSettings.overrideDebugView ? cameraSettings.debugView : settings.debugView
            };
            if (!histories.TryGetValue(camera, out EndfieldCameraHistory history))
            {
                history = new EndfieldCameraHistory();
                histories.Add(camera, history);
            }
            frame.temporalHistory = history;
            frame.temporalEnabled = settings.enableTemporalAA && temporalMaterial && frame.debugView == EndfieldDebugView.Final
                && (!cameraSettings || cameraSettings.enableTemporalAA);
            frame.nonJitteredViewProjection = GL.GetGPUProjectionMatrix(camera.projectionMatrix, true) * camera.worldToCameraMatrix;
            frame.projectionMatrix = frame.temporalEnabled
                ? history.Begin(camera, frame.targets.width, frame.targets.height, cameraSettings ? cameraSettings.temporalResetVersion : 0)
                : camera.projectionMatrix;
            frame.postProcessSource = frame.targets.sceneColor;
            if (!frame.temporalEnabled) history.valid = false;
            try
            {
                frame.targets.Allocate(frame.command, Mathf.NextPowerOfTwo(Mathf.Clamp(settings.shadowAtlasSize, 256, 4096)));
                frame.Flush();
                context.SetupCameraProperties(camera);
                SetCameraGlobals(frame);
                // 先清理所有 MRT 和深度，Outline 与 GBuffer 共用这一次清理。
                frame.command.SetRenderTarget(frame.targets.gbufferAttachments, new RenderTargetIdentifier(frame.targets.depthAttachment));
                frame.command.SetViewport(new Rect(0, 0, frame.targets.width, frame.targets.height));
                frame.command.ClearRenderTarget(true, true, Color.clear);
                frame.Flush();
                foreach (EndfieldRenderPass pass in passes)
                {
                    frame.command.BeginSample(pass.Name);
                    frame.Flush();
                    pass.Execute(frame);
                    frame.command.EndSample(pass.Name);
                    frame.Flush();
                }
                if (frame.temporalEnabled) history.Commit(frame.nonJitteredViewProjection);
#if UNITY_EDITOR
                // 编辑模式静止后也完成有限次积累，不要求用户不断拖动Scene视口。
                if (frame.temporalEnabled && camera.cameraType == CameraType.SceneView && history.NeedsWarmup)
                    UnityEditor.SceneView.RepaintAll();
#endif
            }
            catch { history.valid = false; throw; }
            finally
            {
                frame.targets.Release(frame.command);
                frame.Flush();
                CommandBufferPool.Release(frame.command);
            }
            removedCameras.Clear();
            foreach (var entry in histories) if (!entry.Key) removedCameras.Add(entry.Key);
            foreach (Camera removed in removedCameras) { histories[removed].Dispose(); histories.Remove(removed); }
        }

        static void SetCameraGlobals(EndfieldFrameData frame)
        {
            Camera camera = frame.camera;
            Matrix4x4 projection = GL.GetGPUProjectionMatrix(frame.projectionMatrix, true);
            // 和Unity SRP一致：此API接收CPU投影，底层会转换到GPU投影。
            // GL.GetGPUProjectionMatrix只用于自定义逆矩阵，不能再传回这个API二次翻转。
            frame.command.SetViewProjectionMatrices(camera.worldToCameraMatrix, frame.projectionMatrix);
            frame.command.SetGlobalMatrix("_EndfieldInverseViewProjection", (projection * camera.worldToCameraMatrix).inverse);
            frame.command.SetGlobalMatrix("_EndfieldNonJitteredViewProjection", frame.nonJitteredViewProjection);
            frame.command.SetGlobalMatrix("_EndfieldPreviousViewProjection", frame.temporalHistory.valid ? frame.temporalHistory.previousNonJitteredViewProjection : frame.nonJitteredViewProjection);
            frame.command.SetGlobalMatrix("_TemporalPreviousViewProjection", frame.temporalHistory.valid ? frame.temporalHistory.previousNonJitteredViewProjection : frame.nonJitteredViewProjection);
            frame.command.SetGlobalFloat("_EndfieldHistoryValid", frame.temporalHistory.valid ? 1 : 0);
            frame.command.SetGlobalVector("_WorldSpaceCameraPos", camera.transform.position);
            frame.command.SetGlobalVector("_CameraBackgroundColor", camera.backgroundColor.linear);
            frame.command.SetGlobalVector("_EndfieldScreenSize", new Vector4(frame.targets.width, frame.targets.height, 1f / frame.targets.width, 1f / frame.targets.height));
            frame.command.SetGlobalVector("_SourceScaleBias", new Vector4(1, 1, 0, 0));
            frame.command.SetGlobalInt("_DebugView", (int)frame.debugView);
            EndfieldPostProcessVolume post = frame.volumeStack.GetComponent<EndfieldPostProcessVolume>();
            bool postEnabled = (!frame.cameraSettings || frame.cameraSettings.enablePostProcessing) && post.active;
            frame.command.SetGlobalFloat("_EndfieldSceneExposure", postEnabled ? Mathf.Pow(2, post.exposure.value) : 1f);
            frame.Flush();
        }

        public void Dispose()
        {
            CoreUtils.Destroy(lightingMaterial);
            CoreUtils.Destroy(postMaterial);
            CoreUtils.Destroy(temporalMaterial);
            foreach (var history in histories.Values) history.Dispose();
            histories.Clear();
            colorLutBuilder.Dispose();
        }
    }
}
