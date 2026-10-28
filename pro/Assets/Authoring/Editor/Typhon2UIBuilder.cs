using UnityEditor;

namespace Endfield.Authoring
{
    /// <summary>仅选择离线来源；运行仍使用通用UIComposition与当前相机组件。</summary>
    public static class Typhon2UIBuilder
    {
        [MenuItem("Endfield/Authoring/Build Typhon2 UI Composition")]
        public static void Build() => SI1UIBuilder.BuildForCapture("Typhon2");
    }
}
