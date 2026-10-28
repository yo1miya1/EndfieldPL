using System;
using System.IO;
using System.Linq;
using Endfield.Rendering;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace Endfield.Editor
{
    /// <summary>把已确认的角色阴影语义发布到普通组件；运行时不需要导出资料。</summary>
    public static class EndfieldCharacterShadowAuthoring
    {
        const string PrefabPath = "Assets/Endfield/Content/SI1/Prefabs/SI1.prefab";

        [Serializable]
        public sealed class Profile
        {
            public int sourceEvent, tileResolution;
            public float receiverDepthBiasTexels, receiverNormalBiasTexels, filterRadiusTexels;
            public float casterDepthBias, casterSlopeBias;
        }

        public static void Configure(GameObject character, Profile profile)
        {
            if (profile == null) return;
            var renderers = character.GetComponentsInChildren<Renderer>(true);
            var shadows = character.GetComponent<EndfieldCharacterShadow>();
            if (!shadows) shadows = character.AddComponent<EndfieldCharacterShadow>();
            shadows.receivers = renderers.Where(renderer => renderer.sharedMaterials.Any(material =>
                material && material.IsKeywordEnabled("EF_SOURCE_CHARACTER"))).ToArray();
            shadows.casters = renderers.Where(renderer => renderer.shadowCastingMode != ShadowCastingMode.Off).ToArray();
            // SI-1 914：角色tile为1024；receiver偏移分别为3/6个world texel，过滤半径4个atlas texel。
            // 只发布无量纲语义值；投影和world texel每帧由Unity Light、Renderer.bounds生成。
            shadows.resolution = profile.tileResolution;
            shadows.depthBiasTexels = profile.receiverDepthBiasTexels;
            shadows.normalBiasTexels = profile.receiverNormalBiasTexels;
            shadows.filterRadiusTexels = profile.filterRadiusTexels;
            shadows.strength = 1;
            shadows.rasterDepthBias = profile.casterDepthBias;
            EditorUtility.SetDirty(shadows);
        }

        [MenuItem("Endfield/Authoring/Publish character shadow settings")]
        public static void PublishToExistingSceneAndPrefab()
        {
            var scene = SceneManager.GetActiveScene();
            var character = scene.GetRootGameObjects().First(item => item.name == "SI-1 Character");
            string planPath = Path.GetFullPath(Path.Combine(Application.dataPath,
                "../Authoring/Extracted/SI1/Source/scene-import.json"));
            var plan = JsonUtility.FromJson<EndfieldSceneBuilder.ImportPlan>(File.ReadAllText(planPath));
            Configure(character, plan.characterShadowProfile);
            EditorSceneManager.MarkSceneDirty(scene);
            EditorSceneManager.SaveScene(scene);

            var prefab = PrefabUtility.LoadPrefabContents(PrefabPath);
            try
            {
                Configure(prefab, plan.characterShadowProfile);
                PrefabUtility.SaveAsPrefabAsset(prefab, PrefabPath);
            }
            finally { PrefabUtility.UnloadPrefabContents(prefab); }
            AssetDatabase.SaveAssets();
        }
    }
}
