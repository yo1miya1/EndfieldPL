using System;
using UnityEngine;
using UnityEngine.Rendering;

namespace Endfield.Rendering
{
    [Serializable, VolumeComponentMenu("Endfield/Depth Of Field")]
    public sealed class EndfieldDepthOfFieldVolume : VolumeComponent
    {
        public BoolParameter enabled = new BoolParameter(false);
        [Tooltip("近景完全模糊处；与nearEnd相等或radius为0时关闭近景。")]
        public MinFloatParameter nearStart = new MinFloatParameter(0, 0);
        public MinFloatParameter nearEnd = new MinFloatParameter(0, 0);
        public MinFloatParameter nearRadius = new MinFloatParameter(0, 0);
        [Tooltip("远景CoC从0开始的世界距离。SI-1 CS1742 cb1[2].x=9。")]
        public MinFloatParameter farStart = new MinFloatParameter(9, 0);
        [Tooltip("远景CoC达到1的世界距离。SI-1 CS1742 cb1[2].y=20。")]
        public MinFloatParameter farEnd = new MinFloatParameter(20, 0);
        [Tooltip("源远景模糊幅度：SI-1 CS1742 cb1[2].z=1.4099999666。")]
        public MinFloatParameter farRadius = new MinFloatParameter(1.4099999666f, 0);
    }
}
