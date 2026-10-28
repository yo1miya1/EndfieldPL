using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Endfield.Editor
{
    /// <summary>Lino只选择来源/资产路径；运行Pass与发布实现继续使用共享管线。</summary>
    public static class EndfieldLinoBuilder
    {
        public const string CaptureId = "Lino1";
        public const string ContentRoot = "Assets/Endfield/Content/Lino1";
        public const string SettingsRoot = "Assets/Endfield/Settings/Lino1";
        public const string ScenePath = "Assets/Endfield/Scenes/Lino1.unity";

        [MenuItem("Endfield/Open Lino scene")]
        public static void OpenScene() => EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);

        [MenuItem("Endfield/Authoring/Publish Lino Scene")]
        public static void PublishScene()
        {
            string extracted = Path.GetFullPath(Path.Combine(Application.dataPath, "../Authoring/Extracted/" + CaptureId));
            EndfieldSceneBuilder.BuildScene(CaptureId, extracted, ContentRoot, SettingsRoot, ScenePath,
                profile => Endfield.Authoring.EndfieldSourcePostProcessBuilder.ApplyProfile(profile, CaptureId));
            Endfield.Authoring.SI1UIBuilder.BuildForCapture(CaptureId);
            EditorSceneManager.SaveScene(SceneManager.GetActiveScene(), ScenePath);
            AssetDatabase.SaveAssets();
        }
    }
}
