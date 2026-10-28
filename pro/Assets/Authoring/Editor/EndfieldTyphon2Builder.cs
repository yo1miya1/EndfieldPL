using System.IO;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace Endfield.Editor
{
    /// <summary>Typhon2只提供发布路径和本帧Profile，几何/材质/相机逻辑复用共享发布器。</summary>
    public static class EndfieldTyphon2Builder
    {
        public const string CaptureId = "Typhon2";
        public const string ContentRoot = "Assets/Endfield/Content/Typhon2";
        public const string SettingsRoot = "Assets/Endfield/Settings/Typhon2";
        public const string ScenePath = "Assets/Endfield/Scenes/Typhon2.unity";

        [MenuItem("Endfield/Build/Typhon2 Windows player")]
        public static void BuildPlayer() => EndfieldSceneBuilder.BuildPlayer(ScenePath,
            "tmp/build/Typhon2Windows", "EndfieldTyphon2.exe", "typhon2-player-build.txt");

        [MenuItem("Endfield/Authoring/Publish Typhon2 Scene")]
        public static void PublishScene()
        {
            string extracted = Path.GetFullPath(Path.Combine(Application.dataPath, "../Authoring/Extracted/" + CaptureId));
            EndfieldSceneBuilder.BuildScene(CaptureId, extracted, ContentRoot, SettingsRoot, ScenePath,
                Endfield.Authoring.Typhon2PostProcessBuilder.ApplyProfile);
            Endfield.Authoring.SI1UIBuilder.BuildForCapture(CaptureId);
            // Composition在场景构建后才绑定相机，第二次保存不可省略。
            EditorSceneManager.SaveScene(SceneManager.GetActiveScene(), ScenePath);
            AssetDatabase.SaveAssets();
        }
    }
}
