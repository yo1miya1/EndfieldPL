using System.Collections.Generic;
using UnityEngine;

namespace Endfield.Rendering
{
    // 一个局部阴影组：接收者显式绑定组索引，投影只由实时Light和caster bounds决定。
    [ExecuteAlways, DisallowMultipleComponent]
    public sealed class EndfieldCharacterShadow : MonoBehaviour
    {
        [Header("对象范围")]
        [InspectorName("接收局部阴影的对象"), Tooltip("显式接收本组阴影的Renderer。眼睛可以只接收、不投影；组索引通过PropertyBlock传递，保留对象已有的其它属性。")]
        public Renderer[] receivers;
        [InspectorName("生成局部阴影的对象"), Tooltip("只有此列表中的Renderer生成本组深度图。实际绘制要求对象启用、层级激活、ShadowCastingMode非Off，并且材质提供CharacterShadowCaster Pass。需要外部物体遮挡角色时，把它加入此列表。")]
        public Renderer[] casters;
        [Header("投影与接收参数")]
        [InspectorName("有效投影分辨率"), Range(128, 2048), Tooltip("默认1024×1024。当前图集对所有有效组采用请求中的最高分辨率，另外保留空白边缘供Gather过滤，投影范围只跟随投影对象包围盒和实时主光。")]
        public int resolution = 1024;
        [InspectorName("向光源偏移（纹素）"), Min(0), Tooltip("默认3。按当前投影X方向的世界纹素尺寸换算后，在接收端向主光偏移；不是固定世界毫米值，也不是场景CSM的Light.shadowBias。")]
        public float depthBiasTexels = 3;
        [InspectorName("沿接收法线偏移（纹素）"), Min(0), Tooltip("默认6。接收片元使用GBuffer扰动法线和源角度权重；投影顶点本身不沿艺术法线移动。")]
        public float normalBiasTexels = 6;
        [InspectorName("过滤半径（图集纹素）"), Min(0), Tooltip("默认4。源公式以1/atlasWidth同时换算两个UV轴；2:1图集上对应横向4、纵向2像素，并用16次Gather统计深度。")]
        public float filterRadiusTexels = 4;
        [InspectorName("局部阴影强度"), Range(0, 1), Tooltip("与当前主光的shadowStrength相乘。主光关闭阴影时也关闭本组采样；此值不修改普通场景级联阴影。")]
        public float strength = 1;
        [InspectorName("光栅深度偏置"), Min(0), Tooltip("默认8，为Unity逻辑光栅单位。独立D16图在reverse-Z平台对应原生-8；它不等同于世界距离，投影Pass没有顶点法线偏移。")]
        public float rasterDepthBias = 8;
        internal static readonly List<EndfieldCharacterShadow> Active = new List<EndfieldCharacterShadow>();
        static readonly int IndexProperty = Shader.PropertyToID("_CharacterShadowIndex");
        MaterialPropertyBlock block;

        void OnEnable() { if (!Active.Contains(this)) Active.Add(this); }
        void OnDisable() { Active.Remove(this); SetReceiverIndex(-1); }

        internal void SetReceiverIndex(int index)
        {
            if (receivers == null) return;
            if (block == null) block = new MaterialPropertyBlock();
            foreach (Renderer receiver in receivers)
            {
                if (!receiver) continue;
                receiver.GetPropertyBlock(block);
                block.SetFloat(IndexProperty, index);
                receiver.SetPropertyBlock(block);
            }
        }

        internal bool TryGetCasterBounds(out Bounds bounds)
        {
            // 以显式投影组的当前世界包围盒拟合，不使用观察相机的可见范围。
            bounds = default;
            bool found = false;
            if (casters == null) return false;
            foreach (Renderer caster in casters)
            {
                if (!IsCaster(caster)) continue;
                if (found) bounds.Encapsulate(caster.bounds);
                else { bounds = caster.bounds; found = true; }
            }
            return found;
        }

        internal static bool IsCaster(Renderer caster) => caster && caster.enabled && caster.gameObject.activeInHierarchy
            && caster.shadowCastingMode != UnityEngine.Rendering.ShadowCastingMode.Off;
    }
}
