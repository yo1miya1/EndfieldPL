using UnityEngine.Rendering;

namespace Endfield.Authoring
{
    /// <summary>保持原Typhon2发布入口，参数发布共用多捕获实现。</summary>
    public static class Typhon2PostProcessBuilder
    {
        public static void ApplyProfile(VolumeProfile profile) => EndfieldSourcePostProcessBuilder.ApplyProfile(profile, "Typhon2");
    }
}
