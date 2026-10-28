using UnityEditor;

namespace Endfield.Authoring
{
    /// <summary>选择Lino1离线数据，保持运行UI组件与Shader家族共享。</summary>
    public static class Lino1UIBuilder
    {
        [MenuItem("Endfield/Authoring/Build Lino1 UI Composition")]
        public static void Build() => SI1UIBuilder.BuildForCapture("Lino1");
    }
}
