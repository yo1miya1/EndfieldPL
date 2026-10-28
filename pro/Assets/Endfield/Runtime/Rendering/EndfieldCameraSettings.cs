using UnityEngine;

namespace Endfield.Rendering
{
    [DisallowMultipleComponent, RequireComponent(typeof(Camera))]
    public sealed class EndfieldCameraSettings : MonoBehaviour
    {
        public LayerMask volumeLayerMask = ~0;
        public Transform volumeTrigger;
        public bool enablePostProcessing = true;
        public bool enableTemporalAA = true;
        internal int temporalResetVersion;
        public void ResetTemporalHistory() => temporalResetVersion++;
        public bool overrideDebugView;
        public EndfieldDebugView debugView;
    }
}
