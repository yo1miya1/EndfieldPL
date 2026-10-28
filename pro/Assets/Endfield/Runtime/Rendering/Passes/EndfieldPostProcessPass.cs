using UnityEngine;
using UnityEngine.Rendering;

namespace Endfield.Rendering
{
    internal sealed class EndfieldPostProcessPass : EndfieldRenderPass
    {
        public override string Name => "PostProcess";
        readonly int[] bloomDown = new int[12];
        readonly int[] bloomUp = new int[12];
        readonly int[] bloomWidths = new int[12], bloomHeights = new int[12];
        readonly EndfieldTemporalAAPass temporalAA = new EndfieldTemporalAAPass();

        public EndfieldPostProcessPass()
        {
            for (int index = 0; index < 12; index++)
            {
                bloomDown[index] = Shader.PropertyToID("_EndfieldBloomDown" + index);
                bloomUp[index] = Shader.PropertyToID("_EndfieldBloomUp" + index);
            }
        }

        public override void Execute(EndfieldFrameData frame)
        {
            temporalAA.Execute(frame);
            CommandBuffer command = frame.command;
            EndfieldPostProcessVolume volume = frame.volumeStack.GetComponent<EndfieldPostProcessVolume>();
            bool enabled = !frame.cameraSettings || frame.cameraSettings.enablePostProcessing;
            bool final = frame.debugView == EndfieldDebugView.Final;
            bool basicEnabled = enabled && volume.active;
            command.SetGlobalFloat("_PostExposure", basicEnabled ? Mathf.Pow(2, volume.exposure.value) : 1f);
            command.SetGlobalFloat("_PostContrast", basicEnabled ? volume.contrast.value : 1f);
            command.SetGlobalFloat("_PostSaturation", basicEnabled ? volume.saturation.value : 1f);
            command.SetGlobalFloat("_PostToneMapping", basicEnabled && volume.toneMapping.value ? 1 : 0);
            command.SetGlobalFloat("_PostVignette", basicEnabled ? volume.vignetteIntensity.value : 0);
            command.SetGlobalTexture("_BloomTexture", Texture2D.blackTexture);
            command.SetGlobalVector("_BloomTint", Color.white);
            command.SetGlobalFloat("_BloomIntensity", 0);
            command.SetGlobalFloat("_ColorLutEnabled", 0);
            command.SetGlobalVector("_SourceScaleBias", new Vector4(1, 1, 0, 0));

            int source = frame.postProcessSource;
            EndfieldDepthOfFieldVolume dof = frame.volumeStack.GetComponent<EndfieldDepthOfFieldVolume>();
            if (enabled && final && dof.active && dof.enabled.value)
            {
                command.SetGlobalVector("_DofNearParams", new Vector4(dof.nearStart.value, dof.nearEnd.value, dof.nearRadius.value, 0));
                command.SetGlobalVector("_DofFarParams", new Vector4(dof.farStart.value, dof.farEnd.value, dof.farRadius.value, 0));
                command.SetGlobalFloat("_DofParamsReady", 1);
                frame.targets.AllocateEffect(command, frame.targets.postColor, frame.targets.width, frame.targets.height);
                SetSource(frame, source, frame.targets.width, frame.targets.height);
                SetTarget(frame, frame.targets.postColor, frame.targets.width, frame.targets.height);
                Fullscreen(frame, frame.postMaterial, 4);
                source = frame.targets.postColor;
            }

            EndfieldBloomVolume bloom = frame.volumeStack.GetComponent<EndfieldBloomVolume>();
            if (enabled && final && bloom.active && bloom.enabled.value)
                SourceBloom(frame, bloom, source);
            else if (basicEnabled && final && volume.bloomIntensity.value > 0)
                BasicBloom(frame, volume, source);

            EndfieldColorGradingVolume grading = frame.volumeStack.GetComponent<EndfieldColorGradingVolume>();
            EndfieldSourceDisplayVolume display = frame.volumeStack.GetComponent<EndfieldSourceDisplayVolume>();
            bool useSourceDisplay = enabled && final && display.active && display.enabled.value && frame.colorLutBuilder.IsAvailable;
            if (useSourceDisplay)
            {
                frame.colorLutBuilder.Build(frame, grading);
                command.SetGlobalFloat("_ColorLutEnabled", 1);
                command.SetGlobalFloat("_SourceBloomHighlightSuppression", display.bloomHighlightSuppression.value);
                Vector2 center = display.vignetteCenter.value;
                command.SetGlobalVector("_SourceVignetteCenter", new Vector4(center.x, center.y, 0, display.vignetteAspectBlend.value));
                command.SetGlobalVector("_SourceVignetteShape", new Vector4(display.vignetteRoundness.value,
                    display.vignetteFalloff.value, display.vignetteExponent.value, display.vignetteAspectCompensation.value));
                command.SetGlobalVector("_SourceVignetteColor", display.vignetteColor.value);
            }
            SetSource(frame, source, frame.targets.width, frame.targets.height);
            // UI合成以本帧调色结果为初始场景；先落到独立RT，避免读写反馈。
            frame.targets.AllocateEffect(command, frame.targets.resolvedScene, frame.targets.width, frame.targets.height);
            SetTarget(frame, frame.targets.resolvedScene, frame.targets.width, frame.targets.height);
            if (frame.postMaterial) Fullscreen(frame, frame.postMaterial, !final ? 3 : useSourceDisplay ? 5 : 0);
            else command.Blit(source, frame.targets.resolvedScene);
            command.SetGlobalTexture("_EndfieldUIResolvedSceneTexture", frame.targets.resolvedScene);
            SetSource(frame, frame.targets.resolvedScene, frame.targets.width, frame.targets.height);
            // 此处只处理最终RT与显示目标的方向差，不修改Camera投影来纠正图像。
            bool flip = SystemInfo.graphicsUVStartsAtTop && frame.camera.targetTexture == null;
            command.SetGlobalVector("_SourceScaleBias", flip ? new Vector4(1, -1, 0, 1) : new Vector4(1, 1, 0, 0));
            command.SetGlobalVector("_EndfieldOutputScaleBias", flip ? new Vector4(1, -1, 0, 1) : new Vector4(1, 1, 0, 0));
            RenderTargetIdentifier output = frame.camera.targetTexture
                ? new RenderTargetIdentifier(frame.camera.targetTexture) : new RenderTargetIdentifier(BuiltinRenderTextureType.CameraTarget);
            command.SetRenderTarget(output);
            command.SetViewport(frame.camera.pixelRect);
            if (frame.postMaterial) Fullscreen(frame, frame.postMaterial, 9);
            else command.Blit(frame.targets.resolvedScene, output);
            frame.Flush();
            frame.context.SetupCameraProperties(frame.camera);
            command.SetRenderTarget(output);
            command.SetViewport(frame.camera.pixelRect);
            frame.Flush();
        }

        void SourceBloom(EndfieldFrameData frame, EndfieldBloomVolume volume, int source)
        {
            CommandBuffer command = frame.command;
            float threshold = Mathf.GammaToLinearSpace(volume.thresholdGamma.value);
            float knee = threshold * volume.softKnee.value + .00001f;
            command.SetGlobalVector("_BloomThresholdParams", new Vector4(threshold, threshold - knee, knee * 2, .25f / knee));
            command.SetGlobalFloat("_BloomScatter", volume.scatter.value);
            command.SetGlobalFloat("_BloomIntensity", volume.intensity.value);
            command.SetGlobalVector("_BloomTint", volume.tint.value.linear);
            int width = 0, height = 0;
            int count = 0;
            for (int level = 0; level < volume.maxIterations.value; level++)
            {
                // 源尺寸按完整画面逐层取近整数，如720→45→23→11→6→3，
                // 不是把上一层整数反复除2，后者会让奇数层持续偏小。
                float divisor = 1 << (level + 1);
                width = Mathf.Max(1, Mathf.FloorToInt(frame.targets.width / divisor + .5f));
                height = Mathf.Max(1, Mathf.FloorToInt(frame.targets.height / divisor + .5f));
                bloomWidths[level] = width;
                bloomHeights[level] = height;
                frame.targets.AllocateEffect(command, bloomDown[level], width, height);
                if (level == 0) SetSource(frame, source, frame.targets.width, frame.targets.height);
                else SetSource(frame, bloomDown[level - 1], bloomWidths[level - 1], bloomHeights[level - 1]);
                SetTarget(frame, bloomDown[level], width, height);
                Fullscreen(frame, frame.postMaterial, level == 0 ? 6 : 7);
                count++;
                if (width == 1 && height == 1) break;
            }
            int accumulated = bloomDown[count - 1];
            for (int level = count - 2; level >= 0; level--)
            {
                width = bloomWidths[level]; height = bloomHeights[level];
                frame.targets.AllocateEffect(command, bloomUp[level], width, height);
                SetSource(frame, bloomDown[level], width, height);
                command.SetGlobalTexture("_BloomLowTexture", accumulated);
                command.SetGlobalVector("_BloomLowTexture_TexelSize", new Vector4(1f / bloomWidths[level + 1], 1f / bloomHeights[level + 1],
                    bloomWidths[level + 1], bloomHeights[level + 1]));
                SetTarget(frame, bloomUp[level], width, height);
                Fullscreen(frame, frame.postMaterial, 8);
                accumulated = bloomUp[level];
            }
            command.SetGlobalTexture("_BloomTexture", accumulated);
        }

        static void BasicBloom(EndfieldFrameData frame, EndfieldPostProcessVolume volume, int source)
        {
            CommandBuffer command = frame.command;
            int width = Mathf.Max(1, frame.targets.width / 2), height = Mathf.Max(1, frame.targets.height / 2);
            frame.targets.AllocateEffect(command, frame.targets.bloomA, width, height);
            frame.targets.AllocateEffect(command, frame.targets.bloomB, width, height);
            command.SetGlobalFloat("_BloomIntensity", volume.bloomIntensity.value);
            command.SetGlobalFloat("_BloomThreshold", volume.bloomThreshold.value);
            SetSource(frame, source, frame.targets.width, frame.targets.height);
            SetTarget(frame, frame.targets.bloomA, width, height);
            Fullscreen(frame, frame.postMaterial, 1);
            SetSource(frame, frame.targets.bloomA, width, height);
            command.SetGlobalVector("_BloomBlurDirection", new Vector4(1, 0, 0, 0));
            SetTarget(frame, frame.targets.bloomB, width, height);
            Fullscreen(frame, frame.postMaterial, 2);
            SetSource(frame, frame.targets.bloomB, width, height);
            command.SetGlobalVector("_BloomBlurDirection", new Vector4(0, 1, 0, 0));
            SetTarget(frame, frame.targets.bloomA, width, height);
            Fullscreen(frame, frame.postMaterial, 2);
            command.SetGlobalTexture("_BloomTexture", frame.targets.bloomA);
        }

        static void SetSource(EndfieldFrameData frame, int source, int width, int height)
        {
            frame.command.SetGlobalTexture("_SourceTexture", source);
            frame.command.SetGlobalVector("_SourceTexture_TexelSize", new Vector4(1f / width, 1f / height, width, height));
        }


        static void SetTarget(EndfieldFrameData frame, int target, int width, int height)
        {
            frame.command.SetRenderTarget(target);
            frame.command.SetViewport(new Rect(0, 0, width, height));
        }
    }
}
