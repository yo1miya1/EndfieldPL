using UnityEngine;
using UnityEngine.Rendering;

namespace Endfield.Rendering
{
    // Unity不会把ambientProbe系数保存进Scene YAML，用场景组件保存可编辑的环境语义。
    [ExecuteAlways, DisallowMultipleComponent]
    public sealed class EndfieldEnvironmentLighting : MonoBehaviour
    {
        [ColorUsage(false, true), Tooltip("线性环境辐照度，直接写入Unity标准SH的L0，不额外乘球谐基常数。")]
        public Color linearAmbientRadiance = Color.black;
        AmbientMode previousMode;
        SphericalHarmonicsL2 previousProbe;
        bool applied;

        void OnEnable()
        {
            previousMode = RenderSettings.ambientMode;
            previousProbe = RenderSettings.ambientProbe;
            Apply();
        }

        void OnValidate() { if (isActiveAndEnabled) Apply(); }

        public void Apply()
        {
            var probe = new SphericalHarmonicsL2();
            probe[0, 0] = linearAmbientRadiance.r;
            probe[1, 0] = linearAmbientRadiance.g;
            probe[2, 0] = linearAmbientRadiance.b;
            RenderSettings.ambientMode = AmbientMode.Custom;
            RenderSettings.ambientProbe = probe;
            applied = true;
        }

        void OnDisable()
        {
            if (!applied) return;
            RenderSettings.ambientMode = previousMode;
            RenderSettings.ambientProbe = previousProbe;
            applied = false;
        }
    }
}
