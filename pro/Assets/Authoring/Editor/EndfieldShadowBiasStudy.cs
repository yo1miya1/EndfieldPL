using System;
using System.IO;
using Endfield.Rendering;
using UnityEditor;
using UnityEngine;

namespace Endfield.Editor
{
    /// <summary>只针对已复现的自阴影割裂做同机位偏置隔离，结束恢复真正Light参数。</summary>
    public static class EndfieldShadowBiasStudy
    {
        [Serializable] sealed class Evidence
        {
            public string lightName, presetSource, biasCase, finalCapture, shadowCapture;
            public float originalDepthBias, originalNormalBias, temporaryDepthBias = 1, temporaryNormalBias = 1;
            public Vector3 cameraPosition, cameraForward;
            public float fieldOfView;
        }
        [Serializable] sealed class RecordedCamera
        {
            public Vector3 cameraPosition;
            public Quaternion cameraRotation;
            public Matrix4x4 view, projection;
        }

        public static void CaptureUrpDefaultsAtCurrentView() => Capture(1, 1, "urp-defaults");
        public static void CaptureDepthOnlyAtRecordedView() => Capture(1, 0, "depth1-normal0");
        public static void CapturePublishedAtRecordedView()
        {
            var light = RenderSettings.sun;
            Capture(light.shadowBias, light.shadowNormalBias, "published-character-shadow");
        }

        static void Capture(float depthBias, float normalBias, string biasCase)
        {
            var light = RenderSettings.sun;
            var view = SceneView.lastActiveSceneView;
            if (!light || !view) throw new InvalidOperationException("The source scene sun and current SceneView are required.");
            var camera = view.camera;
            // SceneView底层camera在DomainReload后可能暂为原点。以已复现问题的
            // Camera.Render evidence固定本次对照，不把未重绘的临时camera当作用户机位。
            var recorded = JsonUtility.FromJson<RecordedCamera>(File.ReadAllText(
                Path.Combine(EndfieldEditorBridge.OutputRoot, "skin-shadow-camera.json")));
            Vector3 savedPosition = camera.transform.position;
            Quaternion savedRotation = camera.transform.rotation;
            float savedFieldOfView = camera.fieldOfView, savedNear = camera.nearClipPlane, savedFar = camera.farClipPlane;
            var settings = camera.GetComponent<EndfieldCameraSettings>();
            bool temporarySettings = !settings;
            if (temporarySettings) settings = camera.gameObject.AddComponent<EndfieldCameraSettings>();
            var evidence = new Evidence {
                lightName = light.name, originalDepthBias = light.shadowBias, originalNormalBias = light.shadowNormalBias,
                presetSource = biasCase == "published-character-shadow"
                    ? "Current published Light parameters are preserved. Character receivers use the independent EndfieldCharacterShadow group profile and current bounds/light projection."
                    : biasCase == "urp-defaults"
                        ? "Installed Unity6000.6.3f1 URP UniversalRenderPipelineAsset m_ShadowDepthBias=1.0/m_ShadowNormalBias=1.0"
                        : "Single-variable CSM caster-normal-bias isolation: depthBias=1, normalBias=0; no permanent scene change.",
                biasCase = biasCase, temporaryDepthBias = depthBias, temporaryNormalBias = normalBias,
                cameraPosition = recorded.cameraPosition, cameraForward = recorded.cameraRotation * Vector3.forward,
                fieldOfView = 2 * Mathf.Atan(1 / Mathf.Abs(recorded.projection.m11)) * Mathf.Rad2Deg
            };
            try
            {
                camera.transform.SetPositionAndRotation(recorded.cameraPosition, recorded.cameraRotation);
                camera.fieldOfView = evidence.fieldOfView;
                camera.nearClipPlane = recorded.projection.m23 / (recorded.projection.m22 - 1);
                camera.farClipPlane = recorded.projection.m23 / (recorded.projection.m22 + 1);
                camera.worldToCameraMatrix = recorded.view;
                camera.projectionMatrix = recorded.projection;
                light.shadowBias = depthBias;
                light.shadowNormalBias = normalBias;
                settings.ResetTemporalHistory();
                evidence.finalCapture = EndfieldFrameCapture.Capture(new EndfieldEditorBridge.Request {
                    argument = "scene-current", width = 1200, height = 900, warmupFrames = 32
                });
                evidence.shadowCapture = EndfieldFrameCapture.Capture(new EndfieldEditorBridge.Request {
                    argument = "scene-current", debugView = "Shadow", width = 1200, height = 900, warmupFrames = 1
                });
                File.WriteAllText(Path.Combine(EndfieldEditorBridge.OutputRoot, "skin-shadow-bias-study.json"), JsonUtility.ToJson(evidence, true));
                File.WriteAllText(Path.Combine(EndfieldEditorBridge.OutputRoot, "skin-shadow-bias-" + biasCase + ".json"), JsonUtility.ToJson(evidence, true));
            }
            finally
            {
                light.shadowBias = evidence.originalDepthBias;
                light.shadowNormalBias = evidence.originalNormalBias;
                camera.transform.SetPositionAndRotation(savedPosition, savedRotation);
                camera.fieldOfView = savedFieldOfView; camera.nearClipPlane = savedNear; camera.farClipPlane = savedFar;
                camera.ResetWorldToCameraMatrix(); camera.ResetProjectionMatrix();
                settings.ResetTemporalHistory();
                if (temporarySettings) UnityEngine.Object.DestroyImmediate(settings);
            }
        }
    }
}
