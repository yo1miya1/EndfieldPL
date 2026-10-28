using System;
using System.IO;
using Endfield.Rendering;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace Endfield.Authoring
{
    /// <summary>实际CB在离线阶段转为命名参数；发布后只保留普通VolumeProfile。</summary>
    public static class EndfieldSourcePostProcessBuilder
    {
        [Serializable] sealed class Parameters
        {
            public float exposure;
            public float[] nearDof, farDof, bloomTint, vignetteCenter, vignetteShape, vignetteColor;
            public float bloomThresholdGamma, bloomSoftKnee, bloomScatter, bloomIntensity, bloomHighlightSuppression;
            public int bloomMaxIterations;
            public float vignetteAspectBlend, gradingSaturation, gradingShadowWeight;
        }

        public static void ApplyProfile(VolumeProfile profile, string captureId)
        {
            string path = Path.GetFullPath(Path.Combine(Application.dataPath,
                "../Authoring/Extracted/" + captureId + "/Source/semantic-post-process.json"));
            Parameters p = JsonUtility.FromJson<Parameters>(File.ReadAllText(path));
            // 共用已验证的中性分级准备和组件创建；下面逐项写本capture解码出的值。
            // 共享LUT的saturation/shadows为旧工程GPU核对的非唯一推定，不能伪称找到了producer CB。
            EndfieldPostProcessBuilder.ApplySourceProfile(profile);
            profile.TryGet(out EndfieldPostProcessVolume basic);
            basic.exposure.Override(p.exposure);
            profile.TryGet(out EndfieldDepthOfFieldVolume dof);
            dof.nearStart.Override(p.nearDof[0]); dof.nearEnd.Override(p.nearDof[1]); dof.nearRadius.Override(p.nearDof[2]);
            dof.farStart.Override(p.farDof[0]); dof.farEnd.Override(p.farDof[1]); dof.farRadius.Override(p.farDof[2]);
            profile.TryGet(out EndfieldBloomVolume bloom);
            bloom.thresholdGamma.Override(p.bloomThresholdGamma); bloom.softKnee.Override(p.bloomSoftKnee);
            bloom.scatter.Override(p.bloomScatter); bloom.intensity.Override(p.bloomIntensity);
            bloom.maxIterations.Override(p.bloomMaxIterations);
            // 源cb保存GPU线性颜色；Volume的Bloom运行会取.linear，因此发布边界编码一次。
            bloom.tint.Override(ColorOf(p.bloomTint).gamma);
            profile.TryGet(out EndfieldSourceDisplayVolume display);
            display.bloomHighlightSuppression.Override(p.bloomHighlightSuppression);
            display.vignetteCenter.Override(new Vector2(p.vignetteCenter[0], p.vignetteCenter[1]));
            display.vignetteAspectBlend.Override(p.vignetteAspectBlend);
            display.vignetteRoundness.Override(p.vignetteShape[0]);
            display.vignetteFalloff.Override(p.vignetteShape[1]);
            display.vignetteExponent.Override(p.vignetteShape[2]);
            display.vignetteAspectCompensation.Override(p.vignetteShape[3]);
            display.vignetteColor.Override(ColorOf(p.vignetteColor));
            profile.TryGet(out EndfieldColorGradingVolume grading);
            grading.saturation.Override(p.gradingSaturation);
            grading.shadows.Override(new Vector4(1, 1, 1, p.gradingShadowWeight));
            foreach (VolumeComponent component in profile.components) EditorUtility.SetDirty(component);
            EditorUtility.SetDirty(profile);
        }

        static Color ColorOf(float[] value) => new Color(value[0], value[1], value[2], value.Length > 3 ? value[3] : 1);
    }
}
