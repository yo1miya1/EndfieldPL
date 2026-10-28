using System;
using System.Collections.Generic;
using System.IO;
using Endfield.Editor;
using UnityEngine;
using UnityEngine.Rendering;

namespace Endfield.Authoring
{
    // 针对已观察到的整图阴影故障，只改变真实Renderer开关，并在取证后恢复。
    public static class EndfieldShadowDiagnostics
    {
        [Serializable] sealed class Evidence
        {
            public string[] temporarilyExcluded;
            public string rawShadowCapture;
            public string shadowCapture;
        }

        public static void CaptureWithoutEffectShadows() => Capture(false);
        public static void CaptureOnlyCharacterShadows() => Capture(true);

        static void Capture(bool excludeEnvironmentAndEyes)
        {
            var renderers = new List<Renderer>();
            var previousModes = new List<ShadowCastingMode>();
            var names = new List<string>();
            foreach (Renderer renderer in UnityEngine.Object.FindObjectsByType<Renderer>(FindObjectsSortMode.None))
            {
                bool effect = false;
                foreach (Material material in renderer.sharedMaterials)
                    if (material && (material.IsKeywordEnabled("EF_SOURCE_EFFECT") ||
                        (excludeEnvironmentAndEyes && (material.IsKeywordEnabled("EF_SOURCE_ENVIRONMENT") || material.IsKeywordEnabled("EF_EYE"))))) effect = true;
                if (!effect) continue;
                renderers.Add(renderer);
                previousModes.Add(renderer.shadowCastingMode);
                names.Add(renderer.name);
                renderer.shadowCastingMode = ShadowCastingMode.Off;
            }
            try
            {
                var evidence = new Evidence { temporarilyExcluded = names.ToArray() };
                evidence.rawShadowCapture = EndfieldFrameCapture.Capture(new EndfieldEditorBridge.Request {
                    argument = "debug:RawShadow", width = 1506, height = 846, renderDoc = false
                });
                evidence.shadowCapture = EndfieldFrameCapture.Capture(new EndfieldEditorBridge.Request {
                    argument = "debug:Shadow", width = 1506, height = 846, renderDoc = false
                });
                File.WriteAllText(Path.Combine(EndfieldEditorBridge.OutputRoot,
                    excludeEnvironmentAndEyes ? "shadow-character-isolation.json" : "shadow-effect-isolation.json"), JsonUtility.ToJson(evidence, true));
            }
            finally
            {
                for (int index = 0; index < renderers.Count; index++) renderers[index].shadowCastingMode = previousModes[index];
            }
        }
    }
}
