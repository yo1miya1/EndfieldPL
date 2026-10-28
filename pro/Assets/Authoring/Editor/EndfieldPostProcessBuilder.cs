using Endfield.Rendering;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using System.IO;

namespace Endfield.Authoring
{
    // 一次性把已读出的SI-1语义值写成标准Volume资产；Runtime不解析任何源CB。
    public static class EndfieldPostProcessBuilder
    {
        public static void ApplySourceProfile(VolumeProfile profile)
        {
            var basic = GetOrAdd<EndfieldPostProcessVolume>(profile);
            basic.exposure.Override(0); // PS2148 cb0[27].x=1，转换为EV为0。
            basic.contrast.Override(1);
            basic.saturation.Override(1);
            basic.bloomIntensity.Override(0); // 使用下面独立的源Bloom，避免叠两份。
            basic.vignetteIntensity.Override(0);

            var dof = GetOrAdd<EndfieldDepthOfFieldVolume>(profile);
            dof.enabled.Override(true);
            dof.nearStart.Override(0); dof.nearEnd.Override(0); dof.nearRadius.Override(0);
            dof.farStart.Override(9); dof.farEnd.Override(20); dof.farRadius.Override(1.4099999666f);

            var bloom = GetOrAdd<EndfieldBloomVolume>(profile);
            bloom.enabled.Override(true);
            bloom.thresholdGamma.Override(.75f);
            bloom.softKnee.Override(.5f);
            bloom.scatter.Override(.7699999809f);
            bloom.maxIterations.Override(9);
            bloom.intensity.Override(.3660402298f);
            bloom.tint.Override(new Color(.9999998808f, .9999998808f, .9999998808f, 1));

            var display = GetOrAdd<EndfieldSourceDisplayVolume>(profile);
            display.enabled.Override(true);
            display.bloomHighlightSuppression.Override(0);
            display.vignetteCenter.Override(new Vector2(.5f, .5f));
            display.vignetteAspectBlend.Override(0);
            display.vignetteRoundness.Override(.9000000358f);
            display.vignetteFalloff.Override(2.0499999523f);
            display.vignetteExponent.Override(1.2999999523f);
            display.vignetteAspectCompensation.Override(0);
            display.vignetteColor.Override(new Color(.0666666701f, .0671745762f, .0745098069f, 1));

            // SI-1 LUT与旧成熟LUT逐half有99.700%组件一致、MAE 5.95e-7。
            // 复用旧已GPU验证的非唯一推定语义，不伪称找到了源producer CB。
            var grading = GetOrAdd<EndfieldColorGradingVolume>(profile);
            grading.enabled.Override(true);
            grading.temperature.Override(0); grading.tint.Override(0);
            grading.colorFilter.Override(Color.white);
            grading.hueShift.Override(0); grading.contrast.Override(1);
            grading.saturation.Override(1.08f);
            grading.channelMixerRed.Override(new Vector3(1, 0, 0));
            grading.channelMixerGreen.Override(new Vector3(0, 1, 0));
            grading.channelMixerBlue.Override(new Vector3(0, 0, 1));
            grading.lift.Override(new Vector4(1, 1, 1, 0));
            grading.gamma.Override(new Vector4(1, 1, 1, 0));
            grading.gain.Override(new Vector4(1, 1, 1, 0));
            // Unity SMH: linear(white)+negative weight，得到源推定shadow multiplier。
            grading.shadows.Override(new Vector4(1, 1, 1, -.1052631139755249f));
            grading.midtones.Override(new Vector4(1, 1, 1, 0));
            grading.highlights.Override(new Vector4(1, 1, 1, 0));
            grading.tonalRanges.Override(new Vector4(0, .3f, .55f, 1));
            grading.splitShadows.Override(Color.gray); grading.splitHighlights.Override(Color.gray);
            grading.splitBalance.Override(0);
            foreach (VolumeComponent component in profile.components) EditorUtility.SetDirty(component);
            EditorUtility.SetDirty(profile);
        }

        public static void ApplyPipelineShaders(EndfieldRenderPipelineAsset pipeline)
        {
            pipeline.deferredLightingShader = Shader.Find("Hidden/Endfield/DeferredLighting");
            pipeline.postProcessShader = Shader.Find("Hidden/Endfield/PostProcess");
            pipeline.colorLutShader = Shader.Find("Hidden/Endfield/ColorLut");
            pipeline.temporalAAShader = Shader.Find("Hidden/Endfield/TemporalAA");
            const string defaultMaterialPath = "Assets/Endfield/Settings/DefaultLit.mat";
            pipeline.defaultLitMaterial = AssetDatabase.LoadAssetAtPath<Material>(defaultMaterialPath);
            if (!pipeline.defaultLitMaterial)
            {
                pipeline.defaultLitMaterial = new Material(Shader.Find("Endfield/HybridLit")) { name = "Default Lit" };
                AssetDatabase.CreateAsset(pipeline.defaultLitMaterial, defaultMaterialPath);
            }
            EditorUtility.SetDirty(pipeline);
        }

        public static void ExportGeneratedLutForComparison()
        {
            var pipeline = (EndfieldRenderPipelineAsset)GraphicsSettings.defaultRenderPipeline;
            pipeline.defaultVolumeProfile.TryGet(out EndfieldColorGradingVolume grading);
            var target = new RenderTexture(1024, 32, 0, RenderTextureFormat.ARGBHalf, RenderTextureReadWrite.Linear);
            target.Create();
            var image = new Texture2D(1024, 32, TextureFormat.RGBAHalf, false, true);
            RenderTexture previous = RenderTexture.active;
            var command = new CommandBuffer { name = "Generate semantic source LUT" };
            using var builder = new EndfieldColorLutBuilder(pipeline.colorLutShader);
            try
            {
                builder.Record(command, new RenderTargetIdentifier(target), grading);
                Graphics.ExecuteCommandBuffer(command);
                RenderTexture.active = target;
                image.ReadPixels(new Rect(0, 0, 1024, 32), 0, 0);
                image.Apply(false, false);
                string path = Path.Combine(Endfield.Editor.EndfieldEditorBridge.OutputRoot, "generated-color-lut.raw");
                File.WriteAllBytes(path, image.GetRawTextureData<byte>().ToArray());
            }
            finally
            {
                RenderTexture.active = previous;
                command.Release();
                target.Release();
                Object.DestroyImmediate(target);
                Object.DestroyImmediate(image);
            }
        }

        [MenuItem("Endfield/Apply Source Post Process Profile")]
        public static void Build()
        {
            var pipeline = GraphicsSettings.defaultRenderPipeline as EndfieldRenderPipelineAsset;
            ApplyPipelineShaders(pipeline);
            VolumeProfile profile = pipeline.defaultVolumeProfile;
            if (!profile)
            {
                const string path = "Assets/Endfield/Settings/SourcePostProcess.asset";
                profile = AssetDatabase.LoadAssetAtPath<VolumeProfile>(path);
                if (!profile) { profile = ScriptableObject.CreateInstance<VolumeProfile>(); AssetDatabase.CreateAsset(profile, path); }
                pipeline.defaultVolumeProfile = profile;
            }
            ApplySourceProfile(profile);
            EditorUtility.SetDirty(pipeline);
            AssetDatabase.SaveAssets();
        }

        static T GetOrAdd<T>(VolumeProfile profile) where T : VolumeComponent
        {
            if (!profile.TryGet(out T component))
            {
                component = profile.Add<T>(true);
                AssetDatabase.AddObjectToAsset(component, profile);
            }
            component.active = true;
            return component;
        }
    }
}
