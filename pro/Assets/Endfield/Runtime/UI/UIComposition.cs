using System;
using UnityEngine;

namespace Endfield.UI
{
    [CreateAssetMenu(menuName = "Endfield/UI Composition")]
    public sealed class UIComposition : ScriptableObject
    {
        [Serializable] public sealed class Draw
        {
            public Mesh mesh;
            public Material material;
            [HideInInspector] public int sourceEvent;
            [HideInInspector] public bool scissorEnabled;
            [HideInInspector] public Rect scissor;
        }
        public Vector2Int referenceResolution = new Vector2Int(2560, 1440);
        public Material compositeMaterial;
        public Draw[] draws = Array.Empty<Draw>();
    }
}
