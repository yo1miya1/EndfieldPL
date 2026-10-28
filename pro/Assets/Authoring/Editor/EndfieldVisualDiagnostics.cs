using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace Endfield.Editor
{
    /// <summary>局部画面问题的编辑器取证入口；不写入场景，也不进入运行构建。</summary>
    public static class EndfieldVisualDiagnostics
    {
        [Serializable] sealed class RendererState
        {
            public string name, material;
            public Bounds bounds;
        }
        [Serializable] sealed class SceneState
        {
            public Vector3 cameraPosition, cameraForward;
            public float fieldOfView;
            public RendererState[] renderers;
        }

        public static void ApplyMaterialPasses()
        {
            foreach (string guid in AssetDatabase.FindAssets("t:Material", new[] { "Assets/Endfield/Content" }))
            {
                var material = AssetDatabase.LoadAssetAtPath<Material>(AssetDatabase.GUIDToAssetPath(guid));
                EndfieldMaterialSetup.Apply(material);
                EditorUtility.SetDirty(material);
            }
            AssetDatabase.SaveAssets();
        }

        public static void RecordScene()
        {
            var camera = Camera.main;
            var state = new SceneState {
                cameraPosition = camera.transform.position, cameraForward = camera.transform.forward,
                fieldOfView = camera.fieldOfView,
                renderers = UnityEngine.Object.FindObjectsByType<Renderer>(FindObjectsSortMode.None)
                    .Select(renderer => new RendererState { name = renderer.name, bounds = renderer.bounds,
                        material = renderer.sharedMaterial ? renderer.sharedMaterial.name : "" }).ToArray()
            };
            File.WriteAllText(Path.Combine(EndfieldEditorBridge.OutputRoot, "scene-state.json"), JsonUtility.ToJson(state, true));
        }

        public static void CaptureOutlinePayloadOnly()
        {
            var materials = UnityEngine.Object.FindObjectsByType<Renderer>(FindObjectsSortMode.None)
                .SelectMany(renderer => renderer.sharedMaterials).Where(material => material && material.IsKeywordEnabled("EF_SOURCE_SCREEN_OUTLINE"))
                .Distinct().ToArray();
            var previous = materials.Select(material => material.GetShaderPassEnabled("EndfieldOutlineColor")).ToArray();
            try
            {
                foreach (var material in materials) material.SetShaderPassEnabled("EndfieldOutlineColor", false);
                Camera.main.GetComponent<Endfield.Rendering.EndfieldCameraSettings>().ResetTemporalHistory();
                string folder = EndfieldFrameCapture.Capture(new EndfieldEditorBridge.Request { width = 2560, height = 1440, warmupFrames = 32 });
                File.WriteAllText(Path.Combine(EndfieldEditorBridge.OutputRoot, "outline-payload-only.txt"), folder);
            }
            finally
            {
                for (int i = 0; i < materials.Length; i++) materials[i].SetShaderPassEnabled("EndfieldOutlineColor", previous[i]);
                Camera.main.GetComponent<Endfield.Rendering.EndfieldCameraSettings>().ResetTemporalHistory();
            }
        }
    }
}
