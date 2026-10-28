using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace Endfield.Editor
{
    /// <summary>按材质用途显示参数；仅编辑普通Material，不依赖离线生成工具或捕获资料。</summary>
    public sealed class EndfieldLitShaderGUI : ShaderGUI
    {
        public override void ValidateMaterial(Material material) => EndfieldMaterialSetup.Apply(material);
        readonly Dictionary<string, bool> foldouts = new Dictionary<string, bool>();
        readonly string[] groups = { "基础表面", "物理受光", "角色受光", "环境反射", "皮肤与面部", "发丝",
            "眼睛", "分层衣料", "视差水晶", "环境材质", "效果材质", "描边与阴影", "高级映射" };

        public override void OnGUI(MaterialEditor editor, MaterialProperty[] properties)
        {
            var material = (Material)editor.target;
            EditorGUILayout.LabelField("Endfield 混合材质", EditorStyles.boldLabel);
            DrawFamily(editor, properties, material);
            DrawFeatures(editor, properties, material);
            foreach (string group in groups)
            {
                var visible = new List<MaterialProperty>();
                foreach (var property in properties)
                    if ((property.propertyFlags & UnityEngine.Rendering.ShaderPropertyFlags.HideInInspector) == 0 &&
                        !IsFeature(material.shader, property.name) && Group(property.name) == group)
                        visible.Add(property);
                if (visible.Count == 0 || !IsRelevant(group, material)) continue;
                if (!foldouts.ContainsKey(group)) foldouts[group] = group == "基础表面" || group == "物理受光";
                foldouts[group] = EditorGUILayout.BeginFoldoutHeaderGroup(foldouts[group], group);
                if (foldouts[group])
                {
                    if (group == "环境反射") EditorGUILayout.HelpBox("由场景中的 Reflection Probe 提供环境反射，随物体和相机实时变化。", MessageType.None);
                    foreach (var property in visible) editor.ShaderProperty(property, property.displayName);
                }
                EditorGUILayout.EndFoldoutHeaderGroup();
            }
            DrawRenderState(editor, properties);
            foreach (Material target in editor.targets) EndfieldMaterialSetup.Apply(target);
        }

        static bool IsFeature(Shader shader, string name)
        {
            int index = shader.FindPropertyIndex(name);
            if (index < 0) return false;
            foreach (string attribute in shader.GetPropertyAttributes(index))
                if (attribute.StartsWith("Toggle(", StringComparison.Ordinal)) return true;
            return false;
        }

        void DrawFeatures(MaterialEditor editor, MaterialProperty[] properties, Material material)
        {
            const string title = "着色功能";
            if (!foldouts.ContainsKey(title)) foldouts[title] = false;
            foldouts[title] = EditorGUILayout.BeginFoldoutHeaderGroup(foldouts[title], title);
            if (foldouts[title])
                foreach (var property in properties)
                    if (IsFeature(material.shader, property.name) && property.name != "_Hair" && property.name != "_Cloth" &&
                        property.name != "_Face" && property.name != "_Eye") editor.ShaderProperty(property, property.displayName);
            EditorGUILayout.EndFoldoutHeaderGroup();
        }

        static void DrawFamily(MaterialEditor editor, MaterialProperty[] properties, Material material)
        {
            string[] keywords = { "EF_HAIR", "EF_CLOTH", "EF_FACE", "EF_EYE" };
            string[] names = { "_Hair", "_Cloth", "_Face", "_Eye" };
            int selected = 0;
            for (int i = 0; i < keywords.Length; i++) if (material.IsKeywordEnabled(keywords[i])) selected = i + 1;
            EditorGUI.BeginChangeCheck();
            int next = EditorGUILayout.Popup("着色模型", selected, new[] { "通用表面", "头发", "衣料", "皮肤 / 面部", "眼睛" });
            if (!EditorGUI.EndChangeCheck()) return;
            editor.RegisterPropertyChangeUndo("着色模型");
            for (int i = 0; i < keywords.Length; i++)
            {
                bool enabled = next == i + 1;
                FindProperty(names[i], properties).floatValue = enabled ? 1 : 0;
                foreach (Material target in editor.targets)
                    if (enabled) target.EnableKeyword(keywords[i]); else target.DisableKeyword(keywords[i]);
            }
        }

        static string Group(string name)
        {
            if (name == "_Cull" || name == "_SrcBlend" || name == "_DstBlend" || name == "_ZWrite") return "渲染状态";
            if (name.Contains("Payload") || name.Contains("Tag") || name.EndsWith("OS", StringComparison.Ordinal) ||
                name.Contains("MipBias") || name == "_BackFaceNormal") return "高级映射";
            if (name.StartsWith("_Hair", StringComparison.Ordinal)) return "发丝";
            if (name.StartsWith("_Skin", StringComparison.Ordinal) || name.StartsWith("_ViewTint", StringComparison.Ordinal)) return "皮肤与面部";
            if (name.StartsWith("_Eye", StringComparison.Ordinal)) return "眼睛";
            if (name.StartsWith("_Cloth", StringComparison.Ordinal)) return "分层衣料";
            if (name.StartsWith("_Parallax", StringComparison.Ordinal)) return "视差水晶";
            if (name.StartsWith("_Environment", StringComparison.Ordinal)) return "环境材质";
            if (name.StartsWith("_Effect", StringComparison.Ordinal)) return "效果材质";
            if (name == "_SourceEnvironmentRotation" || name == "_SourceEnvironmentStrength") return "环境反射";
            if (name.StartsWith("_SourceOutline", StringComparison.Ordinal)) return "描边与阴影";
            if (name.StartsWith("_Source", StringComparison.Ordinal) || name == "_LightingRamp" || name == "_AlbedoResponseLut") return "角色受光";
            if (name.StartsWith("_Outline", StringComparison.Ordinal) || name == "_AlphaMap" || name == "_Opacity") return "描边与阴影";
            if (name == "_Metallic" || name == "_Roughness" || name == "_Occlusion" || name == "_Specular" || name == "_NprWeight") return "物理受光";
            return "基础表面";
        }

        static bool IsRelevant(string group, Material material)
        {
            switch (group)
            {
                case "角色受光": return material.IsKeywordEnabled("EF_SOURCE_CHARACTER");
                case "环境反射": return material.IsKeywordEnabled("EF_SOURCE_ENVIRONMENT_REFLECTION");
                case "皮肤与面部": return material.IsKeywordEnabled("EF_SOURCE_SKIN") || material.IsKeywordEnabled("EF_SOURCE_VIEW_TINT");
                case "发丝": return material.IsKeywordEnabled("EF_HAIR");
                case "眼睛": return material.IsKeywordEnabled("EF_EYE");
                case "分层衣料": return material.IsKeywordEnabled("EF_SOURCE_ANISOTROPIC");
                case "视差水晶": return material.IsKeywordEnabled("EF_SOURCE_PARALLAX_GLOW");
                case "环境材质": return material.IsKeywordEnabled("EF_SOURCE_ENVIRONMENT");
                case "效果材质": return material.IsKeywordEnabled("EF_SOURCE_EFFECT");
                default: return true;
            }
        }

        void DrawRenderState(MaterialEditor editor, MaterialProperty[] properties)
        {
            const string title = "渲染状态";
            if (!foldouts.ContainsKey(title)) foldouts[title] = false;
            foldouts[title] = EditorGUILayout.BeginFoldoutHeaderGroup(foldouts[title], title);
            if (foldouts[title])
            {
                editor.ShaderProperty(FindProperty("_Cull", properties), "背面剔除");
                DrawBlend(editor, FindProperty("_SrcBlend", properties), "源混合因子");
                DrawBlend(editor, FindProperty("_DstBlend", properties), "目标混合因子");
                var depth = FindProperty("_ZWrite", properties);
                EditorGUI.BeginChangeCheck();
                bool writeDepth = EditorGUILayout.Toggle("透明阶段写入深度", depth.floatValue != 0);
                if (EditorGUI.EndChangeCheck()) { editor.RegisterPropertyChangeUndo("深度写入"); depth.floatValue = writeDepth ? 1 : 0; }
                editor.RenderQueueField();
            }
            EditorGUILayout.EndFoldoutHeaderGroup();
        }

        static void DrawBlend(MaterialEditor editor, MaterialProperty property, string label)
        {
            EditorGUI.BeginChangeCheck();
            var mode = (UnityEngine.Rendering.BlendMode)EditorGUILayout.EnumPopup(label, (UnityEngine.Rendering.BlendMode)(int)property.floatValue);
            if (EditorGUI.EndChangeCheck()) { editor.RegisterPropertyChangeUndo(label); property.floatValue = (float)mode; }
        }
    }
}
