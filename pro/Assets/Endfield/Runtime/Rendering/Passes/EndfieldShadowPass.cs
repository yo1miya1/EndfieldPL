using System;
using System.Collections.Generic;
using Unity.Collections;
using UnityEngine;
using UnityEngine.Rendering;

namespace Endfield.Rendering
{
    internal sealed class EndfieldShadowPass : EndfieldRenderPass
    {
        public override string Name => "Shadow";
        const int MaxAdditionalLights = 32;
        const int MaxAdditionalSlices = MaxAdditionalLights * 6;
        readonly Matrix4x4[] mainMatrices = new Matrix4x4[4];
        readonly Vector4[] cascadeSpheres = new Vector4[4];
        readonly Matrix4x4[] additionalMatrices = new Matrix4x4[MaxAdditionalSlices];
        readonly Vector4[] additionalRects = new Vector4[MaxAdditionalSlices];
        readonly Vector4[] additionalParameters = new Vector4[MaxAdditionalLights];
        readonly List<Slice> mainSlices = new List<Slice>(4);
        readonly List<Slice> additionalSlices = new List<Slice>(MaxAdditionalSlices);
        readonly List<Request> requests = new List<Request>(MaxAdditionalLights);
        readonly int additionalAtlas = Shader.PropertyToID("_AdditionalLightShadowmapTexture");
        readonly EndfieldCharacterShadowPass characterShadow = new EndfieldCharacterShadowPass();

        struct Request { public int visibleIndex, additionalIndex, faceCount; }
        struct Slice
        {
            public int visibleIndex, splitIndex, tile;
            public Matrix4x4 view, projection;
            public bool valid;
        }

        public override void Execute(EndfieldFrameData frame)
        {
            SelectMainLight(frame);
            mainSlices.Clear(); additionalSlices.Clear(); requests.Clear();
            Array.Clear(additionalParameters, 0, additionalParameters.Length);
            CommandBuffer command = frame.command;
            command.SetGlobalVector("_MainLightShadowParams", Vector4.zero);
            command.SetGlobalFloat("_MainLightShadowFilter", 0);
            int mainAtlasSize = Mathf.NextPowerOfTwo(Mathf.Clamp(frame.settings.shadowAtlasSize, 256, 4096));
            int mainCount = HasCasters(frame, frame.mainLightIndex)
                ? frame.settings.shadowCascadeCount <= 1 ? 1 : frame.settings.shadowCascadeCount <= 2 ? 2 : 4 : 0;
            int mainColumns = mainCount <= 1 ? 1 : 2;
            int additionalSliceCount = GatherAdditionalRequests(frame);
            int additionalAtlasSize = Mathf.NextPowerOfTwo(Mathf.Clamp(frame.settings.additionalShadowAtlasSize, 256, 4096));
            int additionalColumns = Mathf.NextPowerOfTwo(Mathf.CeilToInt(Mathf.Sqrt(Mathf.Max(1, additionalSliceCount))));
            int splitCount = mainCount + additionalSliceCount;

            if (splitCount > 0)
            {
                var splits = new NativeArray<ShadowSplitData>(splitCount, Allocator.Temp);
                var perLight = new NativeArray<LightShadowCasterCullingInfo>(frame.culling.visibleLights.Length, Allocator.Temp);
                try
                {
                    int offset = PrepareMain(frame, mainCount, mainAtlasSize / mainColumns, mainColumns, splits, perLight);
                    PrepareAdditional(frame, additionalAtlasSize, additionalColumns, offset, splits, perLight);
                    // 和Unity6相同：一次提交每个light的split范围，再按light内splitIndex绘制。
                    frame.context.CullShadowCasters(frame.culling, new ShadowCastersCullingInfos { splitBuffer = splits, perLightInfos = perLight });
                    RenderMain(frame, mainAtlasSize, mainColumns);
                    if (additionalSlices.Count > 0) RenderAdditional(frame, additionalAtlasSize, additionalColumns);
                }
                finally { splits.Dispose(); perLight.Dispose(); }
            }
            else ClearAtlas(frame, frame.targets.shadow, mainAtlasSize);

            command.SetGlobalTexture("_MainLightShadowmapTexture", new RenderTargetIdentifier(frame.targets.shadow), RenderTextureSubElement.Depth);
            if (additionalSlices.Count == 0)
                command.SetGlobalTexture(additionalAtlas, new RenderTargetIdentifier(frame.targets.shadow), RenderTextureSubElement.Depth);
            command.SetGlobalVectorArray("_AdditionalLightShadowParams", additionalParameters);
            command.SetGlobalDepthBias(0, 0);
            frame.Flush();
            characterShadow.Execute(frame);
            frame.Flush();
            frame.context.SetupCameraProperties(frame.camera);
            command.SetViewProjectionMatrices(frame.camera.worldToCameraMatrix, frame.projectionMatrix);
            command.SetViewport(new Rect(0, 0, frame.targets.width, frame.targets.height));
            frame.Flush();
        }

        int GatherAdditionalRequests(EndfieldFrameData frame)
        {
            int additionalIndex = 0, slices = 0;
            var lights = frame.culling.visibleLights;
            for (int index = 0; index < lights.Length && additionalIndex < Mathf.Clamp(frame.settings.maxAdditionalLights, 0, MaxAdditionalLights); index++)
            {
                var visible = lights[index];
                if (index == frame.mainLightIndex || (visible.lightType != LightType.Directional && visible.lightType != LightType.Point && visible.lightType != LightType.Spot)) continue;
                if (HasCasters(frame, index))
                {
                    int faces = visible.lightType == LightType.Point ? 6 : 1;
                    requests.Add(new Request { visibleIndex = index, additionalIndex = additionalIndex, faceCount = faces });
                    slices += faces;
                }
                additionalIndex++;
            }
            return slices;
        }

        int PrepareMain(EndfieldFrameData frame, int count, int resolution, int columns,
            NativeArray<ShadowSplitData> splits, NativeArray<LightShadowCasterCullingInfo> perLight)
        {
            if (count == 0) return 0;
            Light light = frame.culling.visibleLights[frame.mainLightIndex].light;
            for (int cascade = 0; cascade < count; cascade++)
            {
                bool valid = frame.culling.ComputeDirectionalShadowMatricesAndCullingPrimitives(frame.mainLightIndex,
                    cascade, count, frame.settings.shadowCascadeSplits, resolution, light.shadowNearPlane,
                    out Matrix4x4 view, out Matrix4x4 projection, out ShadowSplitData split);
                split.shadowCascadeBlendCullingFactor = 1;
                splits[cascade] = split;
                Vector4 sphere = split.cullingSphere; sphere.w *= sphere.w;
                cascadeSpheres[cascade] = sphere;
                mainMatrices[cascade] = EndfieldShadowUtils.AtlasMatrix(projection, view, cascade, columns);
                mainSlices.Add(new Slice { visibleIndex = frame.mainLightIndex, splitIndex = cascade, tile = cascade, view = view, projection = projection, valid = valid });
            }
            perLight[frame.mainLightIndex] = new LightShadowCasterCullingInfo { splitRange = new RangeInt(0, count), projectionType = BatchCullingProjectionType.Orthographic };
            return count;
        }

        void PrepareAdditional(EndfieldFrameData frame, int atlasSize, int columns, int offset,
            NativeArray<ShadowSplitData> splits, NativeArray<LightShadowCasterCullingInfo> perLight)
        {
            int resolution = atlasSize / columns;
            foreach (Request request in requests)
            {
                var visible = frame.culling.visibleLights[request.visibleIndex];
                int firstTile = additionalSlices.Count;
                bool lightValid = true;
                for (int face = 0; face < request.faceCount; face++)
                {
                    Matrix4x4 view, projection; ShadowSplitData split; bool valid;
                    if (visible.lightType == LightType.Point)
                    {
                        valid = frame.culling.ComputePointShadowMatricesAndCullingPrimitives(request.visibleIndex, (CubemapFace)face,
                            EndfieldShadowUtils.PointGuardAngle(resolution, visible.light.shadows == LightShadows.Soft), out view, out projection, out split);
                        // Unity Point API与Spot API的视图Y基底相反，沿URP ExtractPointLightMatrix修正。
                        view.m10 = -view.m10; view.m11 = -view.m11; view.m12 = -view.m12; view.m13 = -view.m13;
                    }
                    else if (visible.lightType == LightType.Spot)
                        valid = frame.culling.ComputeSpotShadowMatricesAndCullingPrimitives(request.visibleIndex, out view, out projection, out split);
                    else
                        valid = frame.culling.ComputeDirectionalShadowMatricesAndCullingPrimitives(request.visibleIndex, 0, 1,
                            Vector3.zero, resolution, visible.light.shadowNearPlane, out view, out projection, out split);
                    split.shadowCascadeBlendCullingFactor = 1;
                    splits[offset + face] = split;
                    int tile = additionalSlices.Count;
                    additionalMatrices[tile] = EndfieldShadowUtils.AtlasMatrix(projection, view, tile, columns);
                    float inset = .5f / atlasSize;
                    additionalRects[tile] = new Vector4((tile % columns) / (float)columns + inset, (tile / columns) / (float)columns + inset,
                        (tile % columns + 1f) / columns - inset, (tile / columns + 1f) / columns - inset);
                    additionalSlices.Add(new Slice { visibleIndex = request.visibleIndex, splitIndex = face, tile = tile, view = view, projection = projection, valid = valid });
                    lightValid &= valid;
                }
                perLight[request.visibleIndex] = new LightShadowCasterCullingInfo { splitRange = new RangeInt(offset, request.faceCount),
                    projectionType = visible.lightType == LightType.Directional ? BatchCullingProjectionType.Orthographic : BatchCullingProjectionType.Perspective };
                additionalParameters[request.additionalIndex] = new Vector4(lightValid ? visible.light.shadowStrength : 0,
                    visible.light.shadows == LightShadows.Soft ? 1 : 0, firstTile, visible.lightType == LightType.Point ? 1 : 0);
                offset += request.faceCount;
            }
        }

        void RenderMain(EndfieldFrameData frame, int atlasSize, int columns)
        {
            ClearAtlas(frame, frame.targets.shadow, atlasSize);
            foreach (Slice slice in mainSlices) DrawSlice(frame, slice, atlasSize / columns, columns);
            if (mainSlices.Count == 0) return;
            Light light = frame.culling.visibleLights[frame.mainLightIndex].light;
            frame.command.SetGlobalMatrixArray("_MainLightWorldToShadow", mainMatrices);
            frame.command.SetGlobalVectorArray("_MainLightShadowCascadeSpheres", cascadeSpheres);
            frame.command.SetGlobalVector("_MainLightShadowParams", new Vector4(light.shadowStrength, mainSlices.Count, 1f / atlasSize,
                Mathf.Min(frame.settings.shadowDistance, frame.camera.farClipPlane)));
            frame.command.SetGlobalFloat("_MainLightShadowFilter", light.shadows == LightShadows.Soft ? 1 : 0);
        }

        void RenderAdditional(EndfieldFrameData frame, int atlasSize, int columns)
        {
            frame.command.GetTemporaryRT(additionalAtlas, new RenderTextureDescriptor(atlasSize, atlasSize, RenderTextureFormat.Shadowmap, 32)
                { shadowSamplingMode = ShadowSamplingMode.CompareDepths, msaaSamples = 1 }, FilterMode.Bilinear);
            frame.targets.RegisterEffect(additionalAtlas);
            ClearAtlas(frame, additionalAtlas, atlasSize);
            foreach (Slice slice in additionalSlices) DrawSlice(frame, slice, atlasSize / columns, columns);
            frame.command.SetGlobalTexture("_AdditionalLightShadowmapTexture", new RenderTargetIdentifier(additionalAtlas), RenderTextureSubElement.Depth);
            frame.command.SetGlobalMatrixArray("_AdditionalLightWorldToShadow", additionalMatrices);
            frame.command.SetGlobalVectorArray("_AdditionalLightShadowRects", additionalRects);
            frame.command.SetGlobalVector("_AdditionalShadowAtlasSize", new Vector4(1f / atlasSize, 1f / atlasSize, atlasSize, atlasSize));
        }

        static void ClearAtlas(EndfieldFrameData frame, int atlas, int size)
        {
            frame.command.SetRenderTarget(new RenderTargetIdentifier(atlas));
            frame.command.SetViewport(new Rect(0, 0, size, size));
            frame.command.ClearRenderTarget(RTClearFlags.Depth, Color.clear, 1f, 0);
            frame.Flush();
        }

        static void DrawSlice(EndfieldFrameData frame, Slice slice, int resolution, int columns)
        {
            if (!slice.valid) return;
            var command = frame.command;
            command.SetViewport(new Rect(slice.tile % columns * resolution, slice.tile / columns * resolution, resolution, resolution));
            command.SetViewProjectionMatrices(slice.view, slice.projection);
            EndfieldShadowUtils.SetCasterGlobals(command, frame.culling.visibleLights[slice.visibleIndex], slice.projection, resolution);
            command.SetGlobalDepthBias(1, 2.5f);
            var draw = new ShadowDrawingSettings(frame.culling, slice.visibleIndex) { splitIndex = slice.splitIndex };
            command.DrawRendererList(frame.context.CreateShadowRendererList(ref draw));
            frame.Flush();
        }

        static bool HasCasters(EndfieldFrameData frame, int index)
        {
            if (index < 0) return false;
            Light light = frame.culling.visibleLights[index].light;
            return light.shadows != LightShadows.None && light.shadowStrength > 0 && frame.culling.GetShadowCasterBounds(index, out _);
        }

        static void SelectMainLight(EndfieldFrameData frame)
        {
            float brightest = -1;
            var lights = frame.culling.visibleLights;
            for (int index = 0; index < lights.Length; index++)
            {
                var visible = lights[index];
                if (visible.lightType != LightType.Directional) continue;
                if (visible.light == RenderSettings.sun) { frame.mainLightIndex = index; return; }
                float intensity = visible.finalColor.maxColorComponent;
                if (intensity > brightest) { brightest = intensity; frame.mainLightIndex = index; }
            }
        }
    }
}
