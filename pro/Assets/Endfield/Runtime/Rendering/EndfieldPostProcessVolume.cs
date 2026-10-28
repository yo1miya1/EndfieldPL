using System;
using UnityEngine;
using UnityEngine.Rendering;

namespace Endfield.Rendering
{
    [Serializable, VolumeComponentMenu("Endfield/Post Process")]
    public sealed class EndfieldPostProcessVolume : VolumeComponent
    {
        [Tooltip("曝光补偿，单位为档。")]
        public ClampedFloatParameter exposure = new ClampedFloatParameter(0f, -10f, 10f);
        public BoolParameter toneMapping = new BoolParameter(true);
        public ClampedFloatParameter contrast = new ClampedFloatParameter(1f, 0f, 2f);
        public ClampedFloatParameter saturation = new ClampedFloatParameter(1f, 0f, 2f);
        public ClampedFloatParameter bloomIntensity = new ClampedFloatParameter(0f, 0f, 5f);
        public MinFloatParameter bloomThreshold = new MinFloatParameter(1f, 0f);
        public ClampedFloatParameter vignetteIntensity = new ClampedFloatParameter(0f, 0f, 1f);
    }
}
