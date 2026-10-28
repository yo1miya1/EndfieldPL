using System;
using UnityEngine;
using UnityEngine.Rendering;

namespace Endfield.Rendering
{
    // 这里保存美术语义；运行时由ColorUtils生成LUT参数，不加载截帧CB或最终LUT像素。
    [Serializable, VolumeComponentMenu("Endfield/Color Grading LUT")]
    public sealed class EndfieldColorGradingVolume : VolumeComponent
    {
        public BoolParameter enabled = new BoolParameter(false);
        public ClampedFloatParameter temperature = new ClampedFloatParameter(0, -100, 100);
        public ClampedFloatParameter tint = new ClampedFloatParameter(0, -100, 100);
        public ColorParameter colorFilter = new ColorParameter(Color.white, true, false, true);
        public ClampedFloatParameter hueShift = new ClampedFloatParameter(0, -180, 180);
        public ClampedFloatParameter saturation = new ClampedFloatParameter(1, 0, 2);
        public ClampedFloatParameter contrast = new ClampedFloatParameter(1, 0, 2);
        public Vector3Parameter channelMixerRed = new Vector3Parameter(new Vector3(1, 0, 0));
        public Vector3Parameter channelMixerGreen = new Vector3Parameter(new Vector3(0, 1, 0));
        public Vector3Parameter channelMixerBlue = new Vector3Parameter(new Vector3(0, 0, 1));
        public Vector4Parameter lift = new Vector4Parameter(new Vector4(1, 1, 1, 0));
        public Vector4Parameter gamma = new Vector4Parameter(new Vector4(1, 1, 1, 0));
        public Vector4Parameter gain = new Vector4Parameter(new Vector4(1, 1, 1, 0));
        public Vector4Parameter shadows = new Vector4Parameter(new Vector4(1, 1, 1, 0));
        public Vector4Parameter midtones = new Vector4Parameter(new Vector4(1, 1, 1, 0));
        public Vector4Parameter highlights = new Vector4Parameter(new Vector4(1, 1, 1, 0));
        public Vector4Parameter tonalRanges = new Vector4Parameter(new Vector4(0, .3f, .55f, 1));
        public ColorParameter splitShadows = new ColorParameter(Color.gray, false, false, true);
        public ColorParameter splitHighlights = new ColorParameter(Color.gray, false, false, true);
        public ClampedFloatParameter splitBalance = new ClampedFloatParameter(0, -100, 100);
        [Header("原始ShaderRead曲线；空值使用数学中性曲线")]
        public TextureParameter masterCurve = new TextureParameter(null);
        public TextureParameter redCurve = new TextureParameter(null);
        public TextureParameter greenCurve = new TextureParameter(null);
        public TextureParameter blueCurve = new TextureParameter(null);
        public TextureParameter hueVsHueCurve = new TextureParameter(null);
        public TextureParameter hueVsSatCurve = new TextureParameter(null);
        public TextureParameter satVsSatCurve = new TextureParameter(null);
        public TextureParameter lumVsSatCurve = new TextureParameter(null);
    }
}
