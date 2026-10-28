using System;
using System.Collections.Generic;
using System.IO;
using Endfield.Rendering;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;

namespace Endfield.Editor
{
    /// <summary>将离线角色流程输出发布为普通 Unity Mesh、Material、Prefab 和 Scene。运行时无需 RDC 或工具。</summary>
    public static class EndfieldSceneBuilder
    {
        const string Content = "Assets/Endfield/Content/SI1";
        const string Settings = "Assets/Endfield/Settings";
        const string ScenePath = "Assets/Endfield/Scenes/SI1.unity";
        static string Extracted => Path.GetFullPath(Path.Combine(Application.dataPath, "../Authoring/Extracted/SI1"));

        [Serializable] public sealed class ImportPlan
        {
            public float[] origin;
            public float[] cameraPosition;
            public float[] cameraRotation;
            public float[] mainLightDirection;
            public float[] mainLightRadiance;
            public float[] ambientRadiance;
            public string environmentReflection;
            public EndfieldCharacterShadowAuthoring.Profile characterShadowProfile;
            public float fieldOfView = 20;
            public float aspect = 1.7777778f;
            public Part[] parts;
        }
        [Serializable] public sealed class Part
        {
            public int sourceEvent;
            public string binary;
            public string vertexColorPath;
            public string normalTangentPath;
            public float[] placement;
            public bool placed;
            public string shader = "Endfield/HybridLit";
            public string materialName;
            public string previousMaterialName;
            public string category;
            public bool castShadows;
            public bool shadowsOnly;
            public string[] keywords;
            public TextureBinding[] textures;
            public Scalar[] scalars;
            public Vector[] vectors;
            public int renderQueue = 2000;
        }
        [Serializable] public sealed class TextureBinding
        {
            public string property, path, nativeImportPath, wrapMode, wrapModeU, wrapModeV, filterMode;
            public bool srgb;
        }
        [Serializable] sealed class NativeTextureImport { public int width, height, mipCount; public string data; }
        [Serializable] public sealed class Scalar { public string property; public float value; }
        [Serializable] public sealed class Vector { public string property; public float[] value; }

        [MenuItem("Endfield/Open SI-1 scene")]
        public static void OpenScene() => EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);

        [MenuItem("Endfield/Authoring/Publish SI1 Scene")]
        public static void PublishScene()
        {
            BuildScene();
            Endfield.Authoring.SI1UIBuilder.Build();
            // UI生成器随后给相机绑定composition；必须把绑定一起保存，否则重新打开会丢失UI。
            EditorSceneManager.SaveScene(UnityEngine.SceneManagement.SceneManager.GetActiveScene(), ScenePath);
        }

        [MenuItem("Endfield/Build/Rebuild SI-1 scene from extracted assets")]
        public static void BuildScene()
        {
            string planPath = Path.Combine(Extracted, "Source/scene-import.json");
            ImportPlan plan = JsonUtility.FromJson<ImportPlan>(File.ReadAllText(planPath));
            Directory.CreateDirectory(Content + "/Meshes");
            Directory.CreateDirectory(Content + "/Materials");
            Directory.CreateDirectory(Content + "/Textures");
            Directory.CreateDirectory(Content + "/Prefabs");
            Directory.CreateDirectory(Settings);
            Directory.CreateDirectory("Assets/Endfield/Scenes");
            AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
            ConfigurePipeline();
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var character = new GameObject("SI-1 Character");
            var environment = new GameObject("Environment");
            var effects = new GameObject("Character Effects");
            effects.transform.SetParent(character.transform, false);
            var publishedTextures = new Dictionary<string, Texture2D>();
            Vector3 origin = BlenderToUnity(V3(plan.origin));
            foreach (Part part in plan.parts)
            {
                var mesh = ReadMesh(Path.Combine(Extracted, "Source", part.binary), part, origin);
                if (!string.IsNullOrEmpty(part.vertexColorPath))
                {
                    using var colorsReader = new BinaryReader(File.OpenRead(Path.Combine(Extracted, part.vertexColorPath)));
                    var colors = new Color[mesh.vertexCount];
                    for (int vertex = 0; vertex < colors.Length; vertex++)
                        colors[vertex] = new Color(colorsReader.ReadSingle(), colorsReader.ReadSingle(), colorsReader.ReadSingle(), colorsReader.ReadSingle());
                    mesh.colors = colors;
                }
                mesh.name = part.materialName;
                string meshPath = Content + "/Meshes/" + mesh.name + ".asset";
                MovePublishedAsset(Content + "/Meshes/SI1_" + part.sourceEvent + ".asset", meshPath);
                if (!string.IsNullOrEmpty(part.previousMaterialName))
                    MovePublishedAsset(Content + "/Meshes/" + part.previousMaterialName + ".asset", meshPath);
                SaveAsset(mesh, meshPath);
                var material = BuildMaterial(part, publishedTextures);
                var instance = new GameObject(part.materialName ?? "Part " + part.sourceEvent);
                var parent = part.category == "Environment" ? environment : part.category == "Effects" ? effects : character;
                instance.transform.SetParent(parent.transform, false);
                instance.AddComponent<MeshFilter>().sharedMesh = AssetDatabase.LoadAssetAtPath<Mesh>(meshPath);
                var renderer = instance.AddComponent<MeshRenderer>();
                renderer.sharedMaterial = material;
                renderer.shadowCastingMode = part.shadowsOnly ? ShadowCastingMode.ShadowsOnly : part.castShadows ? ShadowCastingMode.On : ShadowCastingMode.Off;
                renderer.receiveShadows = true;
            }
            var camera = new GameObject("Main Camera", typeof(Camera), typeof(EndfieldCameraSettings)).GetComponent<Camera>();
            camera.tag = "MainCamera";
            camera.transform.position = BlenderToUnity(V3(plan.cameraPosition)) - origin;
            Matrix4x4 rotation = Matrix(plan.cameraRotation);
            // Blender 相机沿 -Z 观察，局部 +Y 向上；统一换到 Unity 的 Y-up / +Z-forward。
            camera.transform.rotation = Quaternion.LookRotation(BlenderToUnity(-rotation.GetColumn(2)), BlenderToUnity(rotation.GetColumn(1)));
            camera.fieldOfView = plan.fieldOfView;
            // 视口比例由Unity跟随Game窗口/RenderTexture；截帧工具按请求尺寸临时设置并恢复。
            camera.ResetAspect();
            camera.nearClipPlane = 0.1f;
            camera.farClipPlane = 50f;
            camera.allowHDR = true;
            camera.allowMSAA = false;
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = new Color(0.52f, 0.52f, 0.50f, 1);

            var key = new GameObject("Key Light", typeof(Light)).GetComponent<Light>();
            key.type = LightType.Directional;
            var radiance = V3(plan.mainLightRadiance);
            key.intensity = Mathf.Max(radiance.x, Mathf.Max(radiance.y, radiance.z));
            key.color = new Color(radiance.x / key.intensity, radiance.y / key.intensity, radiance.z / key.intensity).gamma;
            key.shadows = LightShadows.Soft;
            key.shadowBias = 0.03f;
            key.shadowNormalBias = 0.12f;
            Vector3 sourceDirection = V3(plan.mainLightDirection);
            Vector3 unityDirection = new Vector3(-sourceDirection.x, sourceDirection.y, -sourceDirection.z);
            key.transform.rotation = Quaternion.LookRotation(-unityDirection, Vector3.up);
            RenderSettings.sun = key;
            // 本帧源程序明确走常量环境分支；将实测辐照度转换结果初始化Unity SH探针。
            // 之后Shader读取Unity逐Renderer的SH绑定，材质不保存固定环境CBuffer。
            var environmentLighting = environment.AddComponent<EndfieldEnvironmentLighting>();
            environmentLighting.linearAmbientRadiance = new Color(plan.ambientRadiance[0], plan.ambientRadiance[1], plan.ambientRadiance[2], 1);
            environmentLighting.Apply();
            if (!string.IsNullOrEmpty(plan.environmentReflection))
                Endfield.Authoring.EndfieldReflectionBuilder.Publish(environment, Path.Combine(Extracted, plan.environmentReflection));

            var volume = new GameObject("Post Process Volume", typeof(Volume)).GetComponent<Volume>();
            volume.isGlobal = true;
            volume.sharedProfile = AssetDatabase.LoadAssetAtPath<VolumeProfile>(Settings + "/EndfieldPostProcess.asset");
            EndfieldCharacterShadowAuthoring.Configure(character, plan.characterShadowProfile);
            PrefabUtility.SaveAsPrefabAsset(character, Content + "/Prefabs/SI1.prefab");
            PrefabUtility.SaveAsPrefabAsset(environment, Content + "/Prefabs/Environment.prefab");
            PrefabUtility.SaveAsPrefabAsset(effects, Content + "/Prefabs/CharacterEffects.prefab");
            EditorSceneManager.SaveScene(scene, ScenePath);
            EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
            AssetDatabase.SaveAssets();
            Selection.activeGameObject = character;
            SceneView.lastActiveSceneView?.FrameSelected();
            Debug.Log("SI-1 scene rebuilt: " + plan.parts.Length + " renderers.");
        }

        public static void ConfigurePipeline()
        {
            PlayerSettings.colorSpace = ColorSpace.Linear;
            PlayerSettings.companyName = "Endfield Learning";
            PlayerSettings.productName = "Endfield Rebuild";
            PlayerSettings.defaultScreenWidth = 2560;
            PlayerSettings.defaultScreenHeight = 1440;
            PlayerSettings.runInBackground = true;
            QualitySettings.antiAliasing = 0;
            var profile = AssetDatabase.LoadAssetAtPath<VolumeProfile>(Settings + "/EndfieldPostProcess.asset");
            if (!profile)
            {
                profile = ScriptableObject.CreateInstance<VolumeProfile>();
                AssetDatabase.CreateAsset(profile, Settings + "/EndfieldPostProcess.asset");
                var post = profile.Add<EndfieldPostProcessVolume>(true);
                post.toneMapping.value = false;
                AssetDatabase.AddObjectToAsset(post, profile);
            }
            var asset = AssetDatabase.LoadAssetAtPath<EndfieldRenderPipelineAsset>(Settings + "/EndfieldPipeline.asset");
            if (!asset)
            {
                asset = ScriptableObject.CreateInstance<EndfieldRenderPipelineAsset>();
                AssetDatabase.CreateAsset(asset, Settings + "/EndfieldPipeline.asset");
            }
            asset.deferredLightingShader = Shader.Find("Hidden/Endfield/DeferredLighting");
            asset.postProcessShader = Shader.Find("Hidden/Endfield/PostProcess");
            asset.defaultVolumeProfile = profile;
            asset.requireOpaqueDepthTexture = true; // SI-1软粒子实际采样不透明深度，与测试用DSV分离。
            Endfield.Authoring.EndfieldPostProcessBuilder.ApplySourceProfile(profile);
            Endfield.Authoring.EndfieldPostProcessBuilder.ApplyPipelineShaders(asset);
            GraphicsSettings.defaultRenderPipeline = asset;
            QualitySettings.renderPipeline = asset;
            EditorUtility.SetDirty(asset);
            AssetDatabase.SaveAssets();
        }

        static Material BuildMaterial(Part part, Dictionary<string, Texture2D> publishedTextures)
        {
            string path = Content + "/Materials/" + (part.materialName ?? "SI1_" + part.sourceEvent) + ".mat";
            MovePublishedAsset(Content + "/Materials/SI1_" + part.sourceEvent + ".mat", path);
            if (!string.IsNullOrEmpty(part.previousMaterialName))
                MovePublishedAsset(Content + "/Materials/" + part.previousMaterialName + ".mat", path);
            var material = AssetDatabase.LoadAssetAtPath<Material>(path);
            Shader shader = Shader.Find(part.shader);
            if (!shader) throw new InvalidOperationException("Missing shader " + part.shader);
            if (!material) { material = new Material(shader); AssetDatabase.CreateAsset(material, path); }
            material.shader = shader;
            material.shaderKeywords = part.keywords ?? Array.Empty<string>();
            material.renderQueue = part.renderQueue;
            if (part.scalars != null) foreach (var value in part.scalars) material.SetFloat(value.property, value.value);
            if (part.vectors != null) foreach (var value in part.vectors)
            {
                var vector = new Vector4(value.value[0], value.value[1], value.value[2], value.value[3]);
                int propertyIndex = shader.FindPropertyIndex(value.property);
                if (propertyIndex >= 0 && shader.GetPropertyType(propertyIndex) == ShaderPropertyType.Color)
                {
                    // 语义清单记录的是源GPU线性颜色。Unity材质Color保存显示颜色，上传时再转线性；
                    // 因此只在发布边界转回gamma，保留Inspector颜色控件与来源实际常量同时正确。
                    Color displayColor = new Color(vector.x, vector.y, vector.z, vector.w).gamma;
                    displayColor.a = vector.w;
                    material.SetColor(value.property, displayColor);
                }
                else material.SetVector(value.property, vector);
            }
            // 关键字是离线映射的功能选择；同步Inspector的Toggle值，避免界面显示与实际变体相反。
            for (int index = 0; index < shader.GetPropertyCount(); index++)
                foreach (string attribute in shader.GetPropertyAttributes(index))
                    if (attribute.StartsWith("Toggle(", StringComparison.Ordinal) && attribute.EndsWith(")", StringComparison.Ordinal))
                    {
                        string keyword = attribute.Substring(7, attribute.Length - 8);
                        material.SetFloat(shader.GetPropertyName(index), material.IsKeywordEnabled(keyword) ? 1 : 0);
                    }
            if (part.textures != null) foreach (var binding in part.textures)
            {
                // 原图只在发布时读取；材质永久引用独立的Unity Texture资产。
                string sourceName = Path.GetFileNameWithoutExtension(binding.path);
                string filename = binding.property.TrimStart('_') + "_" + sourceName + (binding.srgb ? "_color" : "_data");
                TextureWrapMode defaultWrap = binding.property.Contains("Lut") || binding.property.Contains("Ramp") ? TextureWrapMode.Clamp : TextureWrapMode.Repeat;
                if (!string.IsNullOrEmpty(binding.wrapMode)) defaultWrap = (TextureWrapMode)Enum.Parse(typeof(TextureWrapMode), binding.wrapMode);
                TextureWrapMode wrapU = string.IsNullOrEmpty(binding.wrapModeU) ? defaultWrap : (TextureWrapMode)Enum.Parse(typeof(TextureWrapMode), binding.wrapModeU);
                TextureWrapMode wrapV = string.IsNullOrEmpty(binding.wrapModeV) ? defaultWrap : (TextureWrapMode)Enum.Parse(typeof(TextureWrapMode), binding.wrapModeV);
                FilterMode filter = string.IsNullOrEmpty(binding.filterMode) ? FilterMode.Bilinear : (FilterMode)Enum.Parse(typeof(FilterMode), binding.filterMode);
                string previousPath = Content + "/Textures/" + filename + ".asset";
                if (!string.IsNullOrEmpty(binding.wrapModeU) || !string.IsNullOrEmpty(binding.wrapModeV))
                    filename += "_" + wrapU + "_" + wrapV + "_" + filter;
                string texturePath = Content + "/Textures/" + filename + ".asset";
                // 同一资源/采样方式可被多个语义槽复用；不同UV边界需要独立Unity纹理采样设置。
                string textureKey = (binding.nativeImportPath ?? binding.path) + "|" + wrapU + "|" + wrapV + "|" + filter;
                if (publishedTextures.TryGetValue(textureKey, out Texture2D publishedTexture))
                {
                    material.SetTexture(binding.property, publishedTexture);
                    continue;
                }
                MovePublishedAsset(previousPath, texturePath);
                MovePublishedAsset(Content + "/Textures/" + sourceName + (binding.srgb ? "_color" : "_data") + ".asset", texturePath);
                Texture2D texture;
                if (!string.IsNullOrEmpty(binding.nativeImportPath))
                {
                    string importPath = Path.Combine(Extracted, binding.nativeImportPath);
                    var native = JsonUtility.FromJson<NativeTextureImport>(File.ReadAllText(importPath));
                    texture = new Texture2D(native.width, native.height, TextureFormat.RGBAHalf, native.mipCount, true);
                    // GPU线性Half像素按原行序和完整mip链保存，不重压缩、不重生平均mip。
                    texture.LoadRawTextureData(File.ReadAllBytes(Path.Combine(Path.GetDirectoryName(importPath), native.data)));
                    texture.Apply(false, false);
                }
                else
                {
                    // 兼容旧PNG资料：SaveTexture已输出线性像素；srgb字段只记录原SRV。
                    texture = new Texture2D(2, 2, TextureFormat.RGBA32, true, true);
                    ImageConversion.LoadImage(texture, File.ReadAllBytes(Path.Combine(Extracted, binding.path)), false);
                    // PNG加载器按Unity图像原点存储；原D3D shader的UV和LUT坐标以首行起点采样。
                    // 在导入边界恢复源行顺序，避免每份Shader对纹理做不同的临时翻转。
                    var pixels = texture.GetPixels32();
                    for (int row = 0; row < texture.height / 2; ++row)
                        for (int column = 0; column < texture.width; ++column)
                        {
                            int a = row * texture.width + column;
                            int b = (texture.height - row - 1) * texture.width + column;
                            Color32 swap = pixels[a]; pixels[a] = pixels[b]; pixels[b] = swap;
                        }
                    texture.SetPixels32(pixels);
                    texture.Apply(true, false);
                }
                texture.name = filename;
                texture.filterMode = filter;
                texture.wrapModeU = wrapU;
                texture.wrapModeV = wrapV;
                SaveAsset(texture, texturePath);
                publishedTexture = AssetDatabase.LoadAssetAtPath<Texture2D>(texturePath);
                publishedTextures.Add(textureKey, publishedTexture);
                material.SetTexture(binding.property, publishedTexture);
            }
            EndfieldMaterialSetup.Apply(material);
            EditorUtility.SetDirty(material);
            return material;
        }

        static Mesh ReadMesh(string path, Part part, Vector3 origin)
        {
            using var reader = new BinaryReader(File.OpenRead(path));
            int count = reader.ReadInt32(), indexCount = reader.ReadInt32(), uvCount = reader.ReadInt32(), flags = reader.ReadInt32();
            var placement = part.placed ? Matrix(part.placement) : Matrix4x4.identity;
            var normalMatrix = placement.inverse.transpose;
            float handedness = placement.determinant < 0 ? -1 : 1;
            var positions = new Vector3[count];
            var normals = new Vector3[count];
            var tangents = new Vector4[count];
            for (int i = 0; i < count; ++i) positions[i] = BlenderToUnity(placement.MultiplyPoint3x4(ReadV3(reader))) - origin;
            for (int i = 0; i < count; ++i) normals[i] = BlenderToUnity(normalMatrix.MultiplyVector(ReadV3(reader))).normalized;
            for (int i = 0; i < count; ++i)
            {
                Vector3 tangent = BlenderToUnity(placement.MultiplyVector(ReadV3(reader))).normalized;
                tangents[i] = new Vector4(tangent.x, tangent.y, tangent.z, handedness * reader.ReadSingle());
            }
            if (!string.IsNullOrEmpty(part.normalTangentPath))
            {
                // 角色截帧是已蒙皮的静态姿势。原提取器的方向流与真实VS输出不一致，
                // 用离线修正的姿势方向发布普通Mesh；运行时仍由Unity对象矩阵变换N/T。
                // 此流已经处于源世界坐标，不能再次乘placement或把相机方向写进网格。
                using var directions = new BinaryReader(File.OpenRead(Path.Combine(Extracted, part.normalTangentPath)));
                if (directions.BaseStream.Length != count * 7L * sizeof(float))
                    throw new InvalidDataException("Posed normal/tangent stream does not match mesh vertices: " + part.materialName);
                for (int i = 0; i < count; ++i)
                {
                    Vector3 n = ReadV3(directions), t = ReadV3(directions);
                    normals[i] = new Vector3(-n.x, n.y, -n.z).normalized;
                    tangents[i] = new Vector4(-t.x, t.y, -t.z, directions.ReadSingle());
                }
            }
            var mesh = new Mesh { indexFormat = IndexFormat.UInt32, vertices = positions, normals = normals, tangents = tangents };
            for (int layer = 0; layer < uvCount; ++layer)
            {
                var uvs = new List<Vector2>(count);
                for (int i = 0; i < count; ++i) uvs.Add(new Vector2(reader.ReadSingle(), reader.ReadSingle()));
                mesh.SetUVs(layer, uvs);
            }
            if ((flags & 1) != 0) reader.BaseStream.Position += count * 12;
            if ((flags & 2) != 0)
            {
                // endfield solver保留的切线空间平滑法线编码，对应源描边VS输入v4.xy。
                // 它不是普通颜色UV；固定UV2通道供通用SourceOutline使用。
                var outlineNormals = new List<Vector2>(count);
                for (int vertex = 0; vertex < count; vertex++)
                    outlineNormals.Add(new Vector2(reader.ReadSingle(), reader.ReadSingle()));
                mesh.SetUVs(2, outlineNormals);
            }
            var indices = new int[indexCount];
            for (int i = 0; i < indexCount; ++i) indices[i] = reader.ReadInt32();
            // world2保留原IB；本坐标基底det=+1，只有实际placement镜像时才交换绕序。
            if (handedness < 0)
                for (int i = 0; i < indexCount; i += 3)
                {
                    int swap = indices[i + 1]; indices[i + 1] = indices[i + 2]; indices[i + 2] = swap;
                }
            mesh.SetIndices(indices, MeshTopology.Triangles, 0);
            mesh.RecalculateBounds();
            return mesh;
        }

        static Vector3 ReadV3(BinaryReader reader) => new Vector3(reader.ReadSingle(), reader.ReadSingle(), reader.ReadSingle());
        static Vector3 V3(float[] value) => new Vector3(value[0], value[1], value[2]);
        // 整套几何、法线、切线和相机只在导入边界转换一次，不在Shader重复翻转。
        // capture-camera的VP首行X系数为负，沿用其屏幕right约定；只在此边界处理X。
        static Vector3 BlenderToUnity(Vector3 value) => new Vector3(-value.x, value.z, value.y);
        static Matrix4x4 Matrix(float[] values)
        {
            var matrix = Matrix4x4.identity;
            if (values != null) for (int row = 0; row < 4; ++row) for (int column = 0; column < 4; ++column) matrix[row, column] = values[row * 4 + column];
            return matrix;
        }
        static void SaveAsset(UnityEngine.Object asset, string path)
        {
            var existing = AssetDatabase.LoadAssetAtPath<UnityEngine.Object>(path);
            if (existing is Mesh published && asset is Mesh source)
            {
                // 更新原生顶点/索引缓冲，而非仅复制序列化字段；编辑器里已显示的Renderer立即取到新数据。
                published.Clear();
                published.name = source.name;
                published.indexFormat = source.indexFormat;
                published.vertices = source.vertices;
                published.normals = source.normals;
                published.tangents = source.tangents;
                published.colors = source.colors;
                for (int channel = 0; channel < 8; channel++)
                {
                    var values = new List<Vector2>();
                    source.GetUVs(channel, values);
                    if (values.Count > 0) published.SetUVs(channel, values);
                }
                published.SetIndices(source.GetIndices(0), MeshTopology.Triangles, 0);
                published.bounds = source.bounds;
                published.UploadMeshData(false);
                EditorUtility.SetDirty(published);
                UnityEngine.Object.DestroyImmediate(source);
            }
            else if (existing is Texture2D publishedTexture && asset is Texture2D sourceTexture)
            {
                // 纹理同样显式上传；只CopySerialized会让已绑定材质继续采样旧的GPU图像。
                publishedTexture.Reinitialize(sourceTexture.width, sourceTexture.height, sourceTexture.graphicsFormat, sourceTexture.mipmapCount > 1);
                publishedTexture.LoadRawTextureData(sourceTexture.GetRawTextureData<byte>());
                publishedTexture.Apply(false, false);
                publishedTexture.name = sourceTexture.name;
                publishedTexture.filterMode = sourceTexture.filterMode;
                publishedTexture.wrapModeU = sourceTexture.wrapModeU;
                publishedTexture.wrapModeV = sourceTexture.wrapModeV;
                EditorUtility.SetDirty(publishedTexture);
                UnityEngine.Object.DestroyImmediate(sourceTexture);
            }
            else if (existing) { EditorUtility.CopySerialized(asset, existing); EditorUtility.SetDirty(existing); UnityEngine.Object.DestroyImmediate(asset); }
            else AssetDatabase.CreateAsset(asset, path);
        }

        // 首次语义改名保留GUID，已有Prefab与材质引用不会因文件名改变失效。
        static void MovePublishedAsset(string previous, string current)
        {
            if (previous != current && AssetDatabase.LoadMainAssetAtPath(previous) && !AssetDatabase.LoadMainAssetAtPath(current))
                AssetDatabase.MoveAsset(previous, current);
        }

        [MenuItem("Endfield/Build/Windows player")]
        public static void BuildPlayer()
        {
            Directory.CreateDirectory(Path.Combine(EndfieldEditorBridge.Workspace, "tmp/build/Windows"));
            var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
            {
                scenes = new[] { ScenePath }, target = BuildTarget.StandaloneWindows64,
                locationPathName = Path.Combine(EndfieldEditorBridge.Workspace, "tmp/build/Windows/EndfieldRebuild.exe"),
                options = BuildOptions.None
            });
            File.WriteAllText(Path.Combine(EndfieldEditorBridge.OutputRoot, "player-build.txt"),
                report.summary.result + "; errors=" + report.summary.totalErrors + "; bytes=" + report.summary.totalSize);
            if (report.summary.result != BuildResult.Succeeded) throw new InvalidOperationException("Player build failed: " + report.summary.result);
        }
    }
}
