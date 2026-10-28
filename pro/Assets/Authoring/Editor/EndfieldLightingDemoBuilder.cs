using System;
using System.IO;
using Endfield.Rendering;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace Endfield.Editor
{
    /// <summary>保存独立的Unity灯光示例；不修改SI1场景或来源材质。</summary>
    public static class EndfieldLightingDemoBuilder
    {
        const string Folder = "Assets/Endfield/Content/Demos/Lighting";
        public const string ScenePath = "Assets/Endfield/Scenes/MultiLightDemo.unity";
        public const string CharacterScenePath = "Assets/Endfield/Scenes/MultiLightCharacterDemo.unity";

        [MenuItem("Endfield/示例/创建多光源场景")]
        public static void Build() => BuildScene(false);

        [MenuItem("Endfield/示例/创建角色多光源场景")]
        public static void BuildWithCharacter() => BuildScene(true);

        static void BuildScene(bool includeCharacter)
        {
            Directory.CreateDirectory(Folder);
            Directory.CreateDirectory("Assets/Endfield/Scenes");
            AssetDatabase.Refresh();
            Scene previousScene = SceneManager.GetActiveScene();
            AmbientMode previousAmbientMode = RenderSettings.ambientMode;
            var previousAmbientProbe = RenderSettings.ambientProbe;
            Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
            SceneManager.SetActiveScene(scene);
            try
            {
                Material floor = Material("Floor", new Color(.55f, .57f, .6f), 0, .65f);
                Material diffuse = Material("Diffuse", new Color(.65f, .65f, .65f), 0, .5f);
                Material metal = Material("Metal", new Color(.75f, .75f, .75f), .8f, .22f);
                Material rough = Material("Rough", new Color(.5f, .55f, .6f), 0, .8f);
                Primitive("Ground receiver", PrimitiveType.Plane, Vector3.zero, new Vector3(1.2f, 1, 1.2f), floor, false);
                Primitive("Diffuse sphere", PrimitiveType.Sphere, new Vector3(-2, .75f, .5f), Vector3.one * 1.5f, diffuse);
                Primitive("Metal sphere", PrimitiveType.Sphere, new Vector3(2, .75f, .5f), Vector3.one * 1.5f, metal);
                Primitive("Cube occluder", PrimitiveType.Cube, new Vector3(0, .65f, 1.6f), Vector3.one * 1.3f, rough);
                if (includeCharacter)
                {
                    var prefab = AssetDatabase.LoadAssetAtPath<GameObject>("Assets/Endfield/Content/SI1/Prefabs/SI1.prefab");
                    var actor = (GameObject)PrefabUtility.InstantiatePrefab(prefab, scene);
                    actor.name = "Source character under Unity lights";
                    actor.transform.position = new Vector3(0, 0, -1.5f);
                }
                else Primitive("Capsule occluder", PrimitiveType.Capsule, new Vector3(0, 1, -1.5f), Vector3.one, diffuse);

                var key = Light("Key Directional", LightType.Directional, Color.white, 1.2f, new Vector3(0, 5, -3));
                key.transform.rotation = Quaternion.Euler(45, -35, 0);
                RenderSettings.sun = key;
                var fill = Light("Fill Directional", LightType.Directional, new Color(.6f, .75f, 1), .35f, new Vector3(0, 4, 3));
                fill.transform.rotation = Quaternion.Euler(35, 145, 0);
                var point = Light("Blue Point", LightType.Point, new Color(.15f, .4f, 1), 16, new Vector3(-2.2f, 2.2f, -1.2f));
                point.range = 6;
                var spot = Light("Warm Spot", LightType.Spot, new Color(1, .35f, .12f), 24, new Vector3(2.5f, 3.5f, -2));
                spot.range = 9; spot.spotAngle = 48; spot.innerSpotAngle = 30;
                spot.transform.LookAt(new Vector3(1.2f, .5f, .5f));

                var camera = new GameObject("Multi light camera", typeof(Camera), typeof(EndfieldCameraSettings)).GetComponent<Camera>();
                camera.tag = "MainCamera";
                camera.transform.position = includeCharacter ? new Vector3(3, 2.2f, -5) : new Vector3(6, 4.5f, -8);
                camera.transform.LookAt(includeCharacter ? new Vector3(0, 1, -.5f) : new Vector3(0, .8f, 0));
                camera.fieldOfView = includeCharacter ? 40 : 45; camera.nearClipPlane = .1f; camera.farClipPlane = 40;
                camera.clearFlags = CameraClearFlags.SolidColor;
                camera.backgroundColor = new Color(.06f, .075f, .1f);
                var environment = new GameObject("Demo environment", typeof(EndfieldEnvironmentLighting)).GetComponent<EndfieldEnvironmentLighting>();
                environment.linearAmbientRadiance = new Color(.035f, .035f, .035f, 1);
                environment.Apply();
                RenderSettings.skybox = null;
                var volume = new GameObject("Demo post processing", typeof(Volume)).GetComponent<Volume>();
                volume.isGlobal = true; volume.priority = 1000;
                volume.sharedProfile = Profile();
                EditorSceneManager.SaveScene(scene, includeCharacter ? CharacterScenePath : ScenePath);
                AssetDatabase.SaveAssets();
            }
            finally
            {
                EditorSceneManager.CloseScene(scene, true);
                SceneManager.SetActiveScene(previousScene);
                // ambientProbe是运行时属性，恢复原活动场景真正的Unity SH。
                RenderSettings.ambientMode = previousAmbientMode;
                RenderSettings.ambientProbe = previousAmbientProbe;
            }
        }

        static Material Material(string name, Color color, float metallic, float roughness)
        {
            string path = Folder + "/" + name + ".mat";
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (!material) { material = new Material(Shader.Find("Endfield/HybridLit")) { name = name }; AssetDatabase.CreateAsset(material, path); }
            material.shaderKeywords = Array.Empty<string>();
            material.renderQueue = (int)RenderQueue.Geometry;
            material.SetColor("_BaseColor", color);
            material.SetFloat("_Metallic", metallic); material.SetFloat("_Roughness", roughness);
            material.SetFloat("_OutlineWidth", 0);
            EndfieldMaterialSetup.Apply(material);
            EditorUtility.SetDirty(material);
            return material;
        }

        static void Primitive(string name, PrimitiveType type, Vector3 position, Vector3 scale, Material material, bool cast = true)
        {
            var item = GameObject.CreatePrimitive(type);
            item.name = name; item.transform.position = position; item.transform.localScale = scale;
            var renderer = item.GetComponent<Renderer>();
            renderer.sharedMaterial = material;
            renderer.shadowCastingMode = cast ? ShadowCastingMode.On : ShadowCastingMode.Off;
            renderer.receiveShadows = true;
        }

        static Light Light(string name, LightType type, Color color, float intensity, Vector3 position)
        {
            var light = new GameObject(name, typeof(Light)).GetComponent<Light>();
            light.type = type; light.color = color; light.intensity = intensity;
            light.transform.position = position;
            light.shadows = LightShadows.Soft; light.shadowStrength = 1;
            // Unity URP Asset默认depth/normal bias均为1；此为独立示例预设，不改来源场景。
            light.shadowBias = 1; light.shadowNormalBias = 1; light.shadowNearPlane = .1f;
            return light;
        }

        static VolumeProfile Profile()
        {
            const string path = Folder + "/DemoPostProcess.asset";
            var profile = AssetDatabase.LoadAssetAtPath<VolumeProfile>(path);
            if (!profile) { profile = ScriptableObject.CreateInstance<VolumeProfile>(); AssetDatabase.CreateAsset(profile, path); }
            T Component<T>() where T : VolumeComponent => profile.TryGet(out T value) ? value : profile.Add<T>(true);
            var post = Component<EndfieldPostProcessVolume>();
            post.exposure.Override(0); post.contrast.Override(1); post.saturation.Override(1);
            post.toneMapping.Override(true); post.bloomIntensity.Override(0); post.vignetteIntensity.Override(0);
            Component<EndfieldSourceDisplayVolume>().enabled.Override(false);
            Component<EndfieldColorGradingVolume>().enabled.Override(false);
            Component<EndfieldBloomVolume>().enabled.Override(false);
            Component<EndfieldDepthOfFieldVolume>().enabled.Override(false);
            EditorUtility.SetDirty(profile);
            return profile;
        }

        // 验证入口只切换活动Demo场景里的真实Light.enabled，不写Shader常量。
        public static void EnableAllLights() => EnableOnly(null);
        public static void EnableMainOnly() => EnableOnly("Key Directional");
        public static void EnablePointOnly() => EnableOnly("Blue Point");
        public static void EnableSpotOnly() => EnableOnly("Warm Spot");
        public static void EnableSecondaryDirectionalOnly() => EnableOnly("Fill Directional");
        static void EnableOnly(string name)
        {
            Scene scene = SceneManager.GetActiveScene();
            if (!scene.name.StartsWith("MultiLight", StringComparison.Ordinal)) throw new InvalidOperationException("Open a MultiLight demo scene first.");
            foreach (var root in scene.GetRootGameObjects())
                foreach (var light in root.GetComponentsInChildren<Light>(true)) light.enabled = name == null || light.name == name;
            foreach (var root in scene.GetRootGameObjects())
                foreach (var camera in root.GetComponentsInChildren<EndfieldCameraSettings>(true)) camera.ResetTemporalHistory();
        }
    }
}
