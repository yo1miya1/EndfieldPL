using System;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using Endfield.UI;

namespace Endfield.Authoring
{
    // 离线导入器只读取Authoring源数据；发布后的Composition完全引用Unity资产。
    // 源常量先按公式用途拆成命名属性，运行时不读取捕获页、JSON或工具路径。
    public static class SI1UIBuilder
    {
        [Serializable] sealed class Manifest
        {
            public int referenceWidth, referenceHeight;
            public bool requiresSceneBlur;
            public int[] blurDownsamples;
            public float blurHighlightClamp;
            public SourceDraw[] draws;
            public SourceTexture[] textures;
        }
        [Serializable] sealed class SourceTexture
        {
            public int resourceId;
            public string path, viewFormat;
            public bool linear, dds;
        }
        [Serializable] sealed class SemanticParameter { public string name; public float[] values; }
        [Serializable] sealed class SourceBinding { public int slot, resourceId; public string dynamic, path; }
        [Serializable] sealed class SourceDraw
        {
            public int eid, vertexCount, indexCount;
            public string family, vertexPath, indexPath;
            public SemanticParameter[] parameters;
            public SourceBinding[] textures;
            public string[] keywords;
            public FixedState fixedState;
            public bool scissorEnabled;
            public float[] scissor;
            public float alphaReduction;
        }
        [Serializable] sealed class FixedState
        {
            public int srcBlend, dstBlend, srcBlendAlpha, dstBlendAlpha, blendOp, blendOpAlpha;
            public int colorMask, cull, zTest, zWrite, stencilRef, stencilReadMask, stencilWriteMask;
            public int stencilCompFront, stencilCompBack, stencilPassFront, stencilPassBack;
            public int stencilFailFront, stencilFailBack, stencilZFailFront, stencilZFailBack;
        }

        static void MoveLegacy(string source, string destination)
        {
            if (!string.IsNullOrEmpty(AssetDatabase.AssetPathToGUID(source)) && string.IsNullOrEmpty(AssetDatabase.AssetPathToGUID(destination)))
                AssetDatabase.MoveAsset(source, destination);
        }

        static T Save<T>(T value, string path) where T : UnityEngine.Object
        {
            var existing = AssetDatabase.LoadAssetAtPath<T>(path);
            if (existing)
            {
                if (value is Texture2D sourceTexture && existing is Texture2D destinationTexture)
                {
                    // GraphicsFormat重载同时刷新色彩格式和GPU纹理；旧TextureFormat重载会保留旧sRGB标记。
                    destinationTexture.Reinitialize(sourceTexture.width, sourceTexture.height, sourceTexture.graphicsFormat, false);
                    destinationTexture.LoadRawTextureData(sourceTexture.GetRawTextureData<byte>());
                    destinationTexture.Apply(false, false);
                    destinationTexture.name = sourceTexture.name;
                    destinationTexture.filterMode = sourceTexture.filterMode;
                    destinationTexture.wrapMode = sourceTexture.wrapMode;
                }
                else EditorUtility.CopySerialized(value, existing);
                UnityEngine.Object.DestroyImmediate(value);
                EditorUtility.SetDirty(existing);
                return existing;
            }
            AssetDatabase.CreateAsset(value, path);
            return value;
        }

        static Mesh BuildMesh(SourceDraw draw, string source, string destination)
        {
            var bytes = File.ReadAllBytes(Path.Combine(source, draw.vertexPath));
            var vertices = new float[bytes.Length / 4];
            Buffer.BlockCopy(bytes, 0, vertices, 0, bytes.Length);
            var rawIndices = File.ReadAllBytes(Path.Combine(source, draw.indexPath));
            var indices = new uint[rawIndices.Length / 4];
            Buffer.BlockCopy(rawIndices, 0, indices, 0, rawIndices.Length);
            // 十个真实VS输出寄存器：clip float4、颜色float4和八个float4插值通道。
            var attributes = new VertexAttributeDescriptor[10];
            attributes[0] = new VertexAttributeDescriptor(VertexAttribute.Position, VertexAttributeFormat.Float32, 4);
            attributes[1] = new VertexAttributeDescriptor(VertexAttribute.Color, VertexAttributeFormat.Float32, 4);
            for (int i = 0; i < 8; i++)
                attributes[i + 2] = new VertexAttributeDescriptor((VertexAttribute)((int)VertexAttribute.TexCoord0 + i), VertexAttributeFormat.Float32, 4);
            string stem = "UI_" + draw.family + "_" + draw.eid;
            string assetPath = destination + "/Meshes/" + stem + ".asset";
            MoveLegacy(destination + "/Meshes/UI-" + draw.eid + ".asset", assetPath);
            var existing = AssetDatabase.LoadAssetAtPath<Mesh>(assetPath);
            var mesh = existing ? existing : new Mesh();
            // 显式刷新GPU顶点流；CopySerialized仅改序列化对象时可能留下旧Renderer缓冲。
            mesh.Clear(false);
            mesh.name = stem;
            mesh.SetVertexBufferParams(draw.vertexCount, attributes);
            mesh.SetVertexBufferData(vertices, 0, 0, vertices.Length, 0, MeshUpdateFlags.DontRecalculateBounds);
            mesh.SetIndexBufferParams(indices.Length, IndexFormat.UInt32);
            mesh.SetIndexBufferData(indices, 0, 0, indices.Length, MeshUpdateFlags.DontRecalculateBounds);
            mesh.subMeshCount = 1;
            mesh.SetSubMesh(0, new SubMeshDescriptor(0, indices.Length, MeshTopology.Triangles)
            { vertexCount = draw.vertexCount }, MeshUpdateFlags.DontRecalculateBounds);
            mesh.bounds = new Bounds(Vector3.zero, Vector3.one * 100000);
            mesh.UploadMeshData(false);
            if (!existing) AssetDatabase.CreateAsset(mesh, assetPath);
            EditorUtility.SetDirty(mesh);
            return mesh;
        }

        [MenuItem("Endfield/Authoring/Build SI1 UI Composition")]
        public static void Build() => BuildForCapture("SI1");

        // 捕获ID只决定离线输入/发布目录；运行组件与材质没有角色ID分支。
        public static void BuildForCapture(string captureId)
        {
            if (string.IsNullOrWhiteSpace(captureId) || captureId.Any(c => !char.IsLetterOrDigit(c) && c != '_'))
                throw new ArgumentException("Capture ID must be a directory name", nameof(captureId));
            string project = Directory.GetParent(Application.dataPath).FullName;
            string source = Path.Combine(project, "Authoring/Extracted", captureId, "UIPrepared");
            string destination = "Assets/Endfield/Content/" + captureId + "/UI";
            var manifest = JsonUtility.FromJson<Manifest>(File.ReadAllText(Path.Combine(source, "manifest.json")));
            foreach (var folder in new[] { "Meshes", "Materials", "Textures" })
                Directory.CreateDirectory(Path.Combine(project, destination, folder));
            AssetDatabase.Refresh();
            var textures = manifest.textures.ToDictionary(t => t.resourceId, t =>
            {
                string stem = "UIAtlas_" + t.resourceId;
                string assetPath = destination + "/Textures/" + stem + ".asset";
                MoveLegacy(destination + "/Textures/Atlas-" + t.resourceId + ".asset", assetPath);
                // DDS保留原始编码块与mip；不套SaveTexture PNG的线性数值和行翻转规则。
                if (t.dds)
                    return EndfieldDdsImporter.LoadOrCreate(Path.GetFullPath(Path.Combine(source, t.path)), assetPath,
                        "Clamp", "Clamp", "Bilinear", t.viewFormat);
                // RenderDoc SaveTexture已经输出解码线性数值；原SRV标记仅保留为来源证据。
                var texture = new Texture2D(2, 2, TextureFormat.RGBA32, false, true)
                { name = stem, filterMode = FilterMode.Bilinear, wrapMode = TextureWrapMode.Clamp };
                ImageConversion.LoadImage(texture, File.ReadAllBytes(Path.Combine(source, t.path)), false);
                // RenderDoc PNG按D3D顶行顺序保存；LoadImage采用Unity底行像素约定。
                // 在导入时还原纹理行方向，保留源PS的全部UV与导数运算。
                var pixels = texture.GetPixels32();
                int rowWidth = texture.width;
                for (int y = 0; y < texture.height / 2; y++)
                {
                    int opposite = texture.height - 1 - y;
                    for (int x = 0; x < rowWidth; x++)
                    {
                        int a = y * rowWidth + x, b = opposite * rowWidth + x;
                        (pixels[a], pixels[b]) = (pixels[b], pixels[a]);
                    }
                }
                texture.SetPixels32(pixels);
                texture.Apply(false, false);
                return Save(texture, assetPath);
            });
            var composition = ScriptableObject.CreateInstance<UIComposition>();
            composition.name = "UIComposition_" + captureId;
            composition.referenceResolution = new Vector2Int(manifest.referenceWidth, manifest.referenceHeight);
            var compositeShader = Shader.Find("Hidden/Endfield/UI/Composite");
            if (!compositeShader) throw new InvalidOperationException("UI composite shader did not import");
            MoveLegacy(destination + "/Materials/Composite.mat", destination + "/Materials/UI_Composite.mat");
            composition.compositeMaterial = Save(new Material(compositeShader) { name = "UI_Composite" }, destination + "/Materials/UI_Composite.mat");
            if (manifest.requiresSceneBlur)
            {
                var blurShader = Shader.Find("Hidden/Endfield/PostProcess");
                if (!blurShader) throw new InvalidOperationException("UI scene blur shader did not import");
                composition.sceneBlurMaterial = Save(new Material(blurShader) { name = "UI_SceneBlur" }, destination + "/Materials/UI_SceneBlur.mat");
                composition.sceneBlurDownsamples = manifest.blurDownsamples ?? Array.Empty<int>();
                composition.sceneBlurHighlightClamp = manifest.blurHighlightClamp;
            }
            composition.draws = manifest.draws.OrderBy(d => d.eid).Select(draw =>
            {
                var shader = Shader.Find("Endfield/UI/" + draw.family);
                if (!shader) throw new InvalidOperationException("Missing UI family: " + draw.family);
                string stem = "UI_" + draw.family + "_" + draw.eid;
                string materialPath = destination + "/Materials/" + stem + ".mat";
                MoveLegacy(destination + "/Materials/UI-" + draw.eid + ".mat", materialPath);
                var material = new Material(shader) { name = stem };
                foreach (var field in typeof(FixedState).GetFields())
                    if (material.HasProperty("_" + field.Name)) material.SetInt("_" + field.Name, (int)field.GetValue(draw.fixedState));
                if (material.HasProperty("_AlphaReduction")) material.SetFloat("_AlphaReduction", draw.alphaReduction);
                foreach (var parameter in draw.parameters)
                {
                    var value = new Vector4(parameter.values[0], parameter.values[1], parameter.values[2], parameter.values[3]);
                    int propertyIndex = shader.FindPropertyIndex(parameter.name);
                    // 源CB已是GPU线性数值；Color属性的序列化边界须编码一次，避免再次sRGB解码。
                    if (propertyIndex >= 0 && shader.GetPropertyType(propertyIndex) == ShaderPropertyType.Color)
                    {
                        Color encoded = ((Color)value).gamma;
                        encoded.a = value.w;
                        material.SetColor(parameter.name, encoded);
                    }
                    else material.SetVector(parameter.name, value);
                }
                foreach (string keyword in draw.keywords) material.EnableKeyword(keyword);
                foreach (var texture in draw.textures)
                    if (string.IsNullOrEmpty(texture.dynamic) && textures.TryGetValue(texture.resourceId, out var asset))
                        material.SetTexture("_UITexture" + texture.slot, asset);
                material = Save(material, materialPath);
                return new UIComposition.Draw
                {
                    sourceEvent = draw.eid,
                    mesh = BuildMesh(draw, source, destination),
                    material = material,
                    scissorEnabled = draw.scissorEnabled,
                    scissor = new Rect(draw.scissor[0], draw.scissor[1], draw.scissor[2], draw.scissor[3])
                };
            }).ToArray();
            MoveLegacy(destination + "/Composition.asset", destination + "/" + composition.name + ".asset");
            var saved = Save(composition, destination + "/" + composition.name + ".asset");
            var camera = Camera.main ? Camera.main : UnityEngine.Object.FindFirstObjectByType<Camera>();
            if (camera)
            {
                var binding = camera.GetComponent<EndfieldUIComposition>();
                if (!binding) binding = camera.gameObject.AddComponent<EndfieldUIComposition>();
                binding.composition = saved;
                EditorUtility.SetDirty(binding);
                UnityEditor.SceneManagement.EditorSceneManager.MarkSceneDirty(camera.gameObject.scene);
            }
            AssetDatabase.SaveAssets();
            Debug.Log(captureId + " UI composition published: " + saved.draws.Length + " source draws, " +
                manifest.draws.Select(d => d.family).Distinct().Count() + " material families, " +
                manifest.textures.Length + " static atlases. No captured RT pixels.");
        }
    }
}
