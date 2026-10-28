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
        // 模糊只由实际使用该层的composition开启，输入永远是当前相机的实时显示颜色。
        public Material sceneBlurMaterial;
        public int[] sceneBlurDownsamples = Array.Empty<int>();
        public float sceneBlurHighlightClamp = 2.5f;
        public Draw[] draws = Array.Empty<Draw>();
    }
}
