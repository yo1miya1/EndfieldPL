using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace Endfield.Authoring
{
    // 实际GPU绑定缺失时的编辑器取证，不参与运行时渲染。
    public static class EndfieldReflectionDiagnostics
    {
        public static void Dump()
        {
            var lines = new List<string>();
            string TextureInfo(Texture texture) => texture ? $"{texture.name}: {texture.GetType().Name}, {texture.width}x{texture.height}, asset={AssetDatabase.GetAssetPath(texture)}" : "null";
            lines.Add($"default={RenderSettings.defaultReflectionMode}, custom={TextureInfo(RenderSettings.customReflectionTexture)}, intensity={RenderSettings.reflectionIntensity}");
            lines.Add($"defaultTexture={TextureInfo(ReflectionProbe.defaultTexture)}, decode={ReflectionProbe.defaultTextureHDRDecodeValues}");
            if (Camera.main && Camera.main.TryGetCullingParameters(out var parameters)) lines.Add($"cullingOptions={parameters.cullingOptions}");
            foreach (var probe in Object.FindObjectsByType<ReflectionProbe>(FindObjectsSortMode.None))
            {
                lines.Add($"probe={probe.name}, enabled={probe.enabled}, active={probe.gameObject.activeInHierarchy}, mode={probe.mode}, hdr={probe.hdr}, intensity={probe.intensity}, bounds={probe.bounds}");
                lines.Add($"texture={TextureInfo(probe.texture)}, baked={TextureInfo(probe.bakedTexture)}, custom={TextureInfo(probe.customBakedTexture)}, decode={probe.textureHDRDecodeValues}");
            }
            var closest = new List<UnityEngine.Rendering.ReflectionProbeBlendInfo>();
            foreach (var renderer in Object.FindObjectsByType<Renderer>(FindObjectsSortMode.None))
            {
                if (!renderer.name.Contains("599") && !renderer.name.Contains("ClothingSurfaceC")) continue;
                renderer.GetClosestReflectionProbes(closest);
                lines.Add($"renderer={renderer.name}, usage={renderer.reflectionProbeUsage}, bounds={renderer.bounds}, selected={closest.Count}");
                foreach (var entry in closest) lines.Add($"selected={entry.probe.name}, weight={entry.weight}, texture={TextureInfo(entry.probe.texture)}");
            }
            File.WriteAllLines(Path.GetFullPath("../tmp/unity/reflection-diagnostics.txt"), lines);
        }
    }
}
