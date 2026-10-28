using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;
using System.Collections.Generic;

namespace Endfield.Rendering
{
    // 每个相机新建一份，只在当前 Render 调用内有效，绝不保存上一相机的矩阵。
    internal sealed class EndfieldFrameData
    {
        public ScriptableRenderContext context;
        public Camera camera;
        public CullingResults culling;
        public EndfieldRenderPipelineAsset settings;
        public EndfieldCameraSettings cameraSettings;
        public VolumeStack volumeStack;
        public CommandBuffer command;
        public EndfieldCameraTargets targets;
        public Material lightingMaterial, postMaterial;
        public EndfieldColorLutBuilder colorLutBuilder;
        public Material temporalMaterial;
        public EndfieldCameraHistory temporalHistory;
        public bool temporalEnabled;
        public Matrix4x4 projectionMatrix, nonJitteredViewProjection;
        public int postProcessSource;
        public int mainLightIndex = -1;
        public EndfieldDebugView debugView;

        public void Flush()
        {
            context.ExecuteCommandBuffer(command);
            command.Clear();
        }
    }

    // 临时 RT 成对申请和释放；整个相机结束（包括异常路径）均释放。
    internal sealed class EndfieldCameraTargets
    {
        public readonly int width, height;
        public readonly int depthAttachment = Shader.PropertyToID("_EndfieldCameraDepthAttachment");
        public readonly int opaqueDepthTexture = Shader.PropertyToID("_EndfieldOpaqueDepthTexture");
        public readonly int sceneColor = Shader.PropertyToID("_EndfieldSceneColor");
        public readonly int bloomA = Shader.PropertyToID("_EndfieldBloomA");
        public readonly int bloomB = Shader.PropertyToID("_EndfieldBloomB");
        public readonly int shadow = Shader.PropertyToID("_MainLightShadowmapTexture");
        public readonly int postColor = Shader.PropertyToID("_EndfieldPostColor");
        public readonly int colorLut = Shader.PropertyToID("_EndfieldColorLut");
        public readonly int resolvedScene = Shader.PropertyToID("_EndfieldUIResolvedSceneTexture");
        public readonly int[] gbuffer = new int[5];
        public readonly RenderTargetIdentifier[] gbufferAttachments = new RenderTargetIdentifier[5];
        readonly List<int> effectTargets = new List<int>();
        RenderTextureDescriptor depthDescriptor;

        public EndfieldCameraTargets(Camera camera, float scale)
        {
            width = Mathf.Max(1, Mathf.RoundToInt(camera.pixelWidth * scale));
            height = Mathf.Max(1, Mathf.RoundToInt(camera.pixelHeight * scale));
            for (int index = 0; index < 5; index++)
            {
                gbuffer[index] = Shader.PropertyToID("_GBuffer" + index);
                gbufferAttachments[index] = new RenderTargetIdentifier(gbuffer[index]);
            }
        }

        public void Allocate(CommandBuffer command, int shadowSize)
        {
            var color = new RenderTextureDescriptor(width, height)
            {
                graphicsFormat = GraphicsFormat.R16G16B16A16_SFloat,
                depthStencilFormat = GraphicsFormat.None, msaaSamples = 1
            };
            command.GetTemporaryRT(sceneColor, color, FilterMode.Bilinear);
            GraphicsFormat[] formats = {
                GraphicsFormat.B10G11R11_UFloatPack32,
                GraphicsFormat.A2B10G10R10_UNormPack32,
                GraphicsFormat.A2B10G10R10_UNormPack32,
                GraphicsFormat.A2B10G10R10_UNormPack32,
                GraphicsFormat.R8G8B8A8_SRGB
            };
            for (int index = 0; index < formats.Length; index++)
            {
                color.graphicsFormat = SystemInfo.IsFormatSupported(formats[index], GraphicsFormatUsage.Render)
                    ? formats[index] : GraphicsFormat.R16G16B16A16_SFloat;
                command.GetTemporaryRT(gbuffer[index], color, FilterMode.Point);
            }
            depthDescriptor = new RenderTextureDescriptor(width, height)
            {
                graphicsFormat = GraphicsFormat.None,
                depthStencilFormat = SystemInfo.IsFormatSupported(GraphicsFormat.D32_SFloat_S8_UInt, GraphicsFormatUsage.Render)
                    ? GraphicsFormat.D32_SFloat_S8_UInt : GraphicsFormat.D24_UNorm_S8_UInt,
                msaaSamples = 1
            };
            command.GetTemporaryRT(depthAttachment, depthDescriptor, FilterMode.Point);
            command.GetTemporaryRT(shadow, new RenderTextureDescriptor(shadowSize, shadowSize, RenderTextureFormat.Shadowmap, 32)
                { shadowSamplingMode = ShadowSamplingMode.CompareDepths, msaaSamples = 1 }, FilterMode.Bilinear);
        }

        public void Release(CommandBuffer command)
        {
            command.ReleaseTemporaryRT(sceneColor);
            command.ReleaseTemporaryRT(depthAttachment);
            command.ReleaseTemporaryRT(shadow);
            foreach (int target in gbuffer) command.ReleaseTemporaryRT(target);
            foreach (int target in effectTargets) command.ReleaseTemporaryRT(target);
        }

        public void AllocateEffect(CommandBuffer command, int name, int effectWidth, int effectHeight)
        {
            command.GetTemporaryRT(name, new RenderTextureDescriptor(effectWidth, effectHeight)
            {
                graphicsFormat = GraphicsFormat.R16G16B16A16_SFloat,
                depthStencilFormat = GraphicsFormat.None, msaaSamples = 1
            }, FilterMode.Bilinear);
            effectTargets.Add(name);
        }

        public void RegisterEffect(int name) => effectTargets.Add(name);

        public void CopyOpaqueDepthForSampling(CommandBuffer command)
        {
            command.GetTemporaryRT(opaqueDepthTexture, depthDescriptor, FilterMode.Point);
            effectTargets.Add(opaqueDepthTexture);
            // D3D11深度CopyTexture要求整张同格式复制；先解除原DSV附件绑定。
            command.SetRenderTarget(new RenderTargetIdentifier(sceneColor));
            command.CopyTexture(new RenderTargetIdentifier(depthAttachment), new RenderTargetIdentifier(opaqueDepthTexture));
            command.SetGlobalTexture("_CameraDepthTexture", new RenderTargetIdentifier(opaqueDepthTexture), RenderTextureSubElement.Depth);
        }
    }
}
