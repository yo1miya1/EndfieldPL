using System;
using System.Collections.Generic;
using System.IO;
using Endfield.Rendering;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Endfield.Editor
{
    /// <summary>一次比较六种真实Unity灯光状态；截图工具与报告可随Authoring一起移除。</summary>
    public static class EndfieldLightingStudy
    {
        [Serializable] sealed class LightEvidence
        {
            public string name, type, shadows;
            public bool enabled;
            public Vector3 position, eulerAngles;
            public Quaternion rotation;
            public Color color;
            public float intensity, range, spotAngle, innerSpotAngle, shadowStrength, shadowBias, shadowNormalBias;
        }
        [Serializable] sealed class CaseEvidence
        {
            public string name, scene, png, renderDocCaptureDirectory;
            public Vector3 cameraPosition;
            public Quaternion cameraRotation;
            public int width = 1920, height = 1080, warmupFrames = 16;
            public LightEvidence[] lights;
        }
        [Serializable] sealed class StudyEvidence { public string utc, scene; public CaseEvidence[] cases; }
        struct OriginalLight { public Light light; public bool enabled; public LightShadows shadows; }

        public static void CaptureLightingStudy()
        {
            Scene scene = SceneManager.GetActiveScene();
            if (!scene.name.StartsWith("MultiLight", StringComparison.Ordinal))
                throw new InvalidOperationException("Open Assets/Endfield/Scenes/MultiLightDemo.unity before capturing the study.");
            var original = new List<OriginalLight>();
            foreach (var root in scene.GetRootGameObjects())
                foreach (var light in root.GetComponentsInChildren<Light>(true))
                    original.Add(new OriginalLight { light = light, enabled = light.enabled, shadows = light.shadows });
            string directory = Path.Combine(EndfieldEditorBridge.OutputRoot, "lighting-study", DateTime.UtcNow.ToString("yyyyMMdd-HHmmss-fff"));
            Directory.CreateDirectory(directory);
            var cases = new List<CaseEvidence>();
            string[] names = { "01-main", "02-main-point", "03-main-spot", "04-main-fill-directional", "05-all", "06-all-no-shadows" };
            try
            {
                for (int index = 0; index < names.Length; index++)
                {
                    foreach (var state in original)
                    {
                        state.light.enabled = state.light.name == "Key Directional" || index >= 4
                            || (index == 1 && state.light.type == LightType.Point)
                            || (index == 2 && state.light.type == LightType.Spot)
                            || (index == 3 && state.light.name == "Fill Directional");
                        state.light.shadows = index == 5 ? LightShadows.None : state.shadows;
                    }
                    var camera = Camera.main;
                    camera.GetComponent<EndfieldCameraSettings>().ResetTemporalHistory();
                    var snapshots = new List<LightEvidence>();
                    foreach (var state in original)
                    {
                        Light light = state.light;
                        snapshots.Add(new LightEvidence {
                            name = light.name, type = light.type.ToString(), enabled = light.enabled,
                            position = light.transform.position, rotation = light.transform.rotation, eulerAngles = light.transform.eulerAngles,
                            color = light.color, intensity = light.intensity, range = light.range, spotAngle = light.spotAngle,
                            innerSpotAngle = light.innerSpotAngle, shadows = light.shadows.ToString(), shadowStrength = light.shadowStrength,
                            shadowBias = light.shadowBias, shadowNormalBias = light.shadowNormalBias
                        });
                    }
                    string capture = EndfieldFrameCapture.Capture(new EndfieldEditorBridge.Request {
                        id = "lighting-study-" + names[index], width = 1920, height = 1080, warmupFrames = 16, renderDoc = index == 4
                    });
                    string png = Path.Combine(directory, names[index] + ".png");
                    File.Copy(Path.Combine(capture, "editor-camera.png"), png);
                    var evidence = new CaseEvidence { name = names[index], scene = scene.path, png = png,
                        renderDocCaptureDirectory = index == 4 ? capture : null, cameraPosition = camera.transform.position,
                        cameraRotation = camera.transform.rotation, lights = snapshots.ToArray() };
                    cases.Add(evidence);
                    File.WriteAllText(Path.Combine(directory, names[index] + ".json"), JsonUtility.ToJson(evidence, true));
                    File.WriteAllText(Path.Combine(directory, "study.json"), JsonUtility.ToJson(new StudyEvidence {
                        utc = DateTime.UtcNow.ToString("O"), scene = scene.path, cases = cases.ToArray()
                    }, true));
                }
                Debug.Log("Lighting study: " + directory);
            }
            finally
            {
                foreach (var state in original) { state.light.enabled = state.enabled; state.light.shadows = state.shadows; }
                Camera.main.GetComponent<EndfieldCameraSettings>().ResetTemporalHistory();
            }
        }
    }
}
