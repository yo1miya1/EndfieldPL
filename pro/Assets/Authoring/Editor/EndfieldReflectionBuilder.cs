using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace Endfield.Authoring
{
    /// <summary>发布静态环境辐射贴图的完整预滤波mip链，再交由Unity ReflectionProbe绑定给Renderer。</summary>
    public static class EndfieldReflectionBuilder
    {
        [Serializable] sealed class Import
        {
            public int size, mipCount;
            public string data;
        }

        public static void Publish(GameObject environment, string importPath)
        {
            var plan = JsonUtility.FromJson<Import>(File.ReadAllText(importPath));
            string directory = Path.GetDirectoryName(importPath);
            const string assetPath = "Assets/Endfield/Content/SI1/Textures/EnvironmentReflection.asset";
            var cubemap = AssetDatabase.LoadAssetAtPath<Cubemap>(assetPath);
            if (!cubemap)
            {
                cubemap = new Cubemap(plan.size, TextureFormat.RGBAHalf, true) { name = "EnvironmentReflection" };
                AssetDatabase.CreateAsset(cubemap, assetPath);
            }
            // 原始D3D和Unity世界基底相差绕Y轴180度。它在资产导入时转换一次；
            // 运行Shader继续使用Unity当前法线、视线和探针采样，没有捕获坐标分支。
            int[] targetFace = { 1, 0, 2, 3, 5, 4 };
            using var reader = new BinaryReader(File.OpenRead(Path.Combine(directory, plan.data)));
            for (int sourceFace = 0; sourceFace < 6; sourceFace++)
                for (int mip = 0; mip < plan.mipCount; mip++)
                {
                    int size = Mathf.Max(1, plan.size >> mip);
                    var pixels = new Color[size * size];
                    for (int index = 0; index < pixels.Length; index++)
                    {
                        var color = new Color(reader.ReadSingle(), reader.ReadSingle(), reader.ReadSingle(), reader.ReadSingle());
                        // ±Y面需180度转向，其余换面即可。输入为GPU原生行序，不经PNG加载器。
                        int destination = sourceFace == 2 || sourceFace == 3 ? pixels.Length - 1 - index : index;
                        pixels[destination] = color;
                    }
                    cubemap.SetPixels(pixels, (CubemapFace)targetFace[sourceFace], mip);
                }
            cubemap.filterMode = FilterMode.Trilinear;
            cubemap.wrapMode = TextureWrapMode.Clamp;
            cubemap.Apply(false, false); // 保留来源预滤波层，不能用普通平均降采样重新生成。
            EditorUtility.SetDirty(cubemap);

            var probe = environment.AddComponent<ReflectionProbe>();
            probe.mode = ReflectionProbeMode.Custom;
            probe.customBakedTexture = cubemap;
            probe.size = Vector3.one * 20;
            probe.center = new Vector3(0, 1, 0);
            probe.boxProjection = false; // 来源为全局环境Cube，不引入不存在的盒投影校正。
            probe.blendDistance = 0;
            probe.intensity = 1;
            probe.importance = 1;
            RenderSettings.defaultReflectionMode = DefaultReflectionMode.Custom;
            RenderSettings.customReflectionTexture = cubemap;
        }
    }
}
