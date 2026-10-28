using System;
using UnityEngine;
using UnityEngine.Rendering;

namespace Endfield.Rendering
{
    // 仅接收Volume语义，执行原LUT producer数学。原始曲线可复用，LUT结果必须现场生成。
    public sealed class EndfieldColorLutBuilder : IDisposable
    {
        readonly Material material;
        readonly Texture2D identityCurve, halfCurve;
        readonly EndfieldColorGradingVolume neutralSettings;
        public bool IsAvailable => material;

        public EndfieldColorLutBuilder(Shader shader)
        {
            if (!shader) shader = Shader.Find("Hidden/Endfield/ColorLut");
            if (shader) material = CoreUtils.CreateEngineMaterial(shader);
            identityCurve = CreateCurve(false);
            halfCurve = CreateCurve(true);
            neutralSettings = ScriptableObject.CreateInstance<EndfieldColorGradingVolume>();
            neutralSettings.hideFlags = HideFlags.HideAndDontSave;
        }

        static Texture2D CreateCurve(bool constant)
        {
            var texture = new Texture2D(128, 1, TextureFormat.RHalf, false, true) {
                name = constant ? "Neutral color curve" : "Identity color curve",
                filterMode = FilterMode.Bilinear, wrapMode = TextureWrapMode.Clamp,
                hideFlags = HideFlags.HideAndDontSave
            };
            var pixels = new Color[128];
            for (int index = 0; index < pixels.Length; index++)
            {
                // 原128点曲线为i/128；producer自己加0.5/128采样中心偏移。
                // 写成i/127会与源中性定义不符，尤其改变高光响应。
                float value = constant ? .5f : (float)index / 128;
                pixels[index] = new Color(value, 0, 0, 1);
            }
            texture.SetPixels(pixels);
            texture.Apply(false, true);
            return texture;
        }

        internal void Build(EndfieldFrameData frame, EndfieldColorGradingVolume volume)
        {
            frame.targets.AllocateEffect(frame.command, frame.targets.colorLut, 1024, 32);
            Record(frame.command, new RenderTargetIdentifier(frame.targets.colorLut), volume);
        }

        // 目标纹理归调用方持有；编辑器预览和运行相机共用同一套语义生成入口。
        public void Record(CommandBuffer command, RenderTargetIdentifier target, EndfieldColorGradingVolume volume)
        {
            if (!volume.enabled.value) volume = neutralSettings;
            command.SetGlobalVector("_ColorLutGeneratorParams", new Vector4(32, .5f / 1024, .5f / 32, 32f / 31));
            command.SetGlobalVector("_ColorLutWhiteBalance", ColorUtils.ColorBalanceToLMSCoeffs(volume.temperature.value, volume.tint.value));
            command.SetGlobalVector("_ColorLutFilter", volume.colorFilter.value.linear);
            command.SetGlobalVector("_ColorLutMixerRed", volume.channelMixerRed.value);
            command.SetGlobalVector("_ColorLutMixerGreen", volume.channelMixerGreen.value);
            command.SetGlobalVector("_ColorLutMixerBlue", volume.channelMixerBlue.value);
            command.SetGlobalVector("_ColorLutHueSaturationContrast", new Vector4(volume.hueShift.value / 360, volume.saturation.value, volume.contrast.value, 0));
            var (lift, gamma, gain) = ColorUtils.PrepareLiftGammaGain(volume.lift.value, volume.gamma.value, volume.gain.value);
            command.SetGlobalVector("_ColorLutLift", lift);
            command.SetGlobalVector("_ColorLutGamma", gamma);
            command.SetGlobalVector("_ColorLutGain", gain);
            var (shadows, midtones, highlights) = ColorUtils.PrepareShadowsMidtonesHighlights(volume.shadows.value, volume.midtones.value, volume.highlights.value);
            command.SetGlobalVector("_ColorLutShadows", shadows);
            command.SetGlobalVector("_ColorLutMidtones", midtones);
            command.SetGlobalVector("_ColorLutHighlights", highlights);
            command.SetGlobalVector("_ColorLutRanges", volume.tonalRanges.value);
            var (splitShadows, splitHighlights) = ColorUtils.PrepareSplitToning(volume.splitShadows.value, volume.splitHighlights.value, volume.splitBalance.value);
            command.SetGlobalVector("_ColorLutSplitShadows", splitShadows);
            command.SetGlobalVector("_ColorLutSplitHighlights", splitHighlights);
            Texture[] curves = {
                volume.masterCurve.value, volume.redCurve.value, volume.greenCurve.value, volume.blueCurve.value,
                volume.hueVsHueCurve.value, volume.hueVsSatCurve.value, volume.satVsSatCurve.value, volume.lumVsSatCurve.value
            };
            for (int index = 0; index < curves.Length; index++)
                command.SetGlobalTexture("_EF_LutCurve" + index, curves[index] ? curves[index] : index < 4 ? identityCurve : halfCurve);
            command.SetRenderTarget(target);
            command.SetViewport(new Rect(0, 0, 1024, 32));
            command.DrawProcedural(Matrix4x4.identity, material, 0, MeshTopology.Triangles, 3);
            command.SetGlobalTexture("_ColorLutTexture", target);
            command.SetGlobalVector("_ColorLutParams", new Vector4(1f / 1024, 1f / 32, 31, 1));
        }

        public void Dispose()
        {
            CoreUtils.Destroy(material);
            CoreUtils.Destroy(identityCurve);
            CoreUtils.Destroy(halfCurve);
            CoreUtils.Destroy(neutralSettings);
        }
    }
}
