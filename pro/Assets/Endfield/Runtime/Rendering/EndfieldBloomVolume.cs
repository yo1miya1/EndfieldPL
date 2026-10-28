using System;
using UnityEngine;
using UnityEngine.Rendering;

namespace Endfield.Rendering
{
    [Serializable, VolumeComponentMenu("Endfield/Source Bloom")]
    public sealed class EndfieldBloomVolume : VolumeComponent
    {
        public BoolParameter enabled = new BoolParameter(false);
        [Tooltip("输入为sRGB阈值；0.75转换后为SI-1 CS1960 cb1[1].x约0.5225216。")]
        public MinFloatParameter thresholdGamma = new MinFloatParameter(.75f, 0);
        public ClampedFloatParameter softKnee = new ClampedFloatParameter(.5f, 0, 1);
        [Tooltip("每层上采样混合，SI-1 CS2041至2104 cb0[0].x=0.77。")]
        public ClampedFloatParameter scatter = new ClampedFloatParameter(.7699999809f, 0, 1);
        [Tooltip("SI-1从1280x720到5x3，共9层；实际尺寸由当前相机计算。")]
        public ClampedIntParameter maxIterations = new ClampedIntParameter(9, 1, 12);
        [Tooltip("SI-1 PS2148 cb1[9].x；不再用手调亮度替代。")]
        public MinFloatParameter intensity = new MinFloatParameter(.3660402298f, 0);
        public ColorParameter tint = new ColorParameter(Color.white, true, false, true);
    }
}
