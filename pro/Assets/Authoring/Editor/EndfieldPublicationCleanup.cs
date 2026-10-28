using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

namespace Endfield.Editor
{
    /// <summary>归档重构过程中已被替换的发布资产；场景、独立Prefab和管线设置的依赖均保留。</summary>
    public static class EndfieldPublicationCleanup
    {
        [Serializable] sealed class Entry { public string asset, guid; }
        [Serializable] sealed class Report { public string reason; public Entry[] assets; }

        [MenuItem("Endfield/Authoring/Archive superseded published assets")]
        public static void ArchiveSupersededAssets()
        {
            AssetDatabase.SaveAssets();
            string[] roots = AssetDatabase.FindAssets("t:Scene", new[] { "Assets/Endfield/Scenes" })
                .Concat(AssetDatabase.FindAssets("t:Prefab", new[] { "Assets/Endfield/Content" }))
                .Concat(AssetDatabase.FindAssets("", new[] { "Assets/Endfield/Settings" }))
                .Select(AssetDatabase.GUIDToAssetPath).Where(path => !AssetDatabase.IsValidFolder(path)).Distinct().ToArray();
            var used = new HashSet<string>(AssetDatabase.GetDependencies(roots, true), StringComparer.OrdinalIgnoreCase);
            var retired = AssetDatabase.FindAssets("", new[] { "Assets/Endfield/Content" })
                .Select(guid => new Entry { asset = AssetDatabase.GUIDToAssetPath(guid), guid = guid })
                .Where(entry => !AssetDatabase.IsValidFolder(entry.asset) && !used.Contains(entry.asset) &&
                    (entry.asset.EndsWith(".asset", StringComparison.OrdinalIgnoreCase) || entry.asset.EndsWith(".mat", StringComparison.OrdinalIgnoreCase)))
                .ToArray();
            string project = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            string sourceRoot = Path.GetFullPath(Path.Combine(project, "Assets/Endfield/Content")) + Path.DirectorySeparatorChar;
            string archive = Path.GetFullPath(Path.Combine(project, "Authoring/RetiredPublished", DateTime.UtcNow.ToString("yyyyMMdd-HHmmss")));
            Directory.CreateDirectory(archive);
            AssetDatabase.StartAssetEditing();
            try
            {
                foreach (var entry in retired)
                {
                    string source = Path.GetFullPath(Path.Combine(project, entry.asset));
                    string destination = Path.GetFullPath(Path.Combine(archive, entry.asset.Substring("Assets/Endfield/Content/".Length)));
                    if (!source.StartsWith(sourceRoot, StringComparison.OrdinalIgnoreCase) ||
                        !destination.StartsWith(archive + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                        throw new InvalidOperationException("Publication archive path escaped its content root.");
                    Directory.CreateDirectory(Path.GetDirectoryName(destination));
                    File.Move(source, destination);
                    File.Move(source + ".meta", destination + ".meta");
                }
            }
            finally { AssetDatabase.StopAssetEditing(); }
            File.WriteAllText(Path.Combine(archive, "manifest.json"), JsonUtility.ToJson(new Report
            {
                reason = "Superseded generated content not referenced by retained scenes, prefabs or pipeline settings. Original files and GUIDs preserved here.",
                assets = retired
            }, true));
            AssetDatabase.Refresh();
            Debug.Log("Archived " + retired.Length + " superseded published assets to " + archive);
        }
    }
}
