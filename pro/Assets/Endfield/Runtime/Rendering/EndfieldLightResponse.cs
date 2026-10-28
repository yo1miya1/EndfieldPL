using UnityEngine;

namespace Endfield.Rendering
{
    /// <summary>附加于原生 Light 的美术受光响应；位置、颜色、强度、范围、锥角及阴影仍由 Light 管理。</summary>
    [DisallowMultipleComponent, RequireComponent(typeof(Light))]
    public sealed class EndfieldLightResponse : MonoBehaviour
    {
        public enum ResponseMode { Surface = 0, RoughnessSpecular = 2, RimDiffuse = 3, ColorBlend = 4 }

        [Tooltip("Surface：普通表面受光；RoughnessSpecular：按粗糙度控制附加高光；RimDiffuse：仅轮廓漫反射；ColorBlend：将已累积表面色混合到灯光颜色。")]
        public ResponseMode response;
        [Tooltip("ColorBlend的替换强度；RimDiffuse的边缘区间；RoughnessSpecular的粗糙度门限；Surface的漫反射过渡。")]
        public float responseStrength;
        [Range(0, 1), Tooltip("RoughnessSpecular中镜面alpha向0.01混合的权重。")]
        public float specularRoughnessBlend;
        [Tooltip("RimDiffuse 中表面漫反能量的混合权重：从常量0.5混合到当前漫反能量。")]
        public float surfaceColorWeight = 1;
        [Tooltip("ColorBlend 的径向衰减幂，已在离线边界从源参数换算为实际幂。")]
        public float radialFalloffPower = 2;
        [Tooltip("小于零采用有限逆平方衰减；非负值采用范围内的径向幂衰减。")]
        public float falloffExponent = -1;
        [Tooltip("ColorBlend 中法线方向对替换权重的影响。")]
        public float normalResponseWeight;
        [Min(0), Tooltip("该灯附加高光的乘数。")]
        public float specularScale = 1;
        [Tooltip("受光计算顺序；颜色替换与累加不可交换。只改变着色求值顺序，不改变 Unity 剔除或阴影索引。")]
        public int evaluationOrder;
    }
}
