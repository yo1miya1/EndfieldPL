using UnityEngine;

namespace Endfield.UI
{
    [DisallowMultipleComponent, RequireComponent(typeof(Camera))]
    public sealed class EndfieldUIComposition : MonoBehaviour
    {
        public UIComposition composition;
    }
}
