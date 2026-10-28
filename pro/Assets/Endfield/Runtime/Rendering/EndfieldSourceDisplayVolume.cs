using System;
using UnityEngine;
using UnityEngine.Rendering;

namespace Endfield.Rendering
{
    [Serializable, VolumeComponentMenu("Endfield/Source Display")]
    public sealed class EndfieldSourceDisplayVolume : VolumeComponent
    {
        public BoolParameter enabled = new BoolParameter(false);
        [Tooltip("SI-1 PS2148 cb1[9].z；合成Bloom时场景高光抑制比例。")]
        public ClampedFloatParameter bloomHighlightSuppression = new ClampedFloatParameter(0, 0, 1);
        public Vector2Parameter vignetteCenter = new Vector2Parameter(new Vector2(.5f, .5f));
        public ClampedFloatParameter vignetteAspectBlend = new ClampedFloatParameter(0, 0, 1);
        public MinFloatParameter vignetteRoundness = new MinFloatParameter(.9000000358f, 0);
        public MinFloatParameter vignetteFalloff = new MinFloatParameter(2.0499999523f, 0);
        public MinFloatParameter vignetteExponent = new MinFloatParameter(1.2999999523f, 0);
        public ClampedFloatParameter vignetteAspectCompensation = new ClampedFloatParameter(0, 0, 1);
        [Tooltip("源PS2148 cb1[4].xyz；原显示公式颜色，按原值传递。")]
        public ColorParameter vignetteColor = new ColorParameter(new Color(.0666666701f, .0671745762f, .0745098069f, 1), true, false, true);
    }
}
