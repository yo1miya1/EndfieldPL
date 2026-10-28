using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Experimental.Rendering;
using UnityEngine.Rendering;

namespace Endfield.Rendering
{
    // Shadow阶段的独立局部图集。它不使用观察相机的frustum，也不复用CSM的偏置/PCF。
    internal sealed class EndfieldCharacterShadowPass : EndfieldRenderPass
    {
        public override string Name => "Character Shadow";
        const int MaxGroups = 16;
        readonly int atlas = Shader.PropertyToID("_CharacterShadowmapTexture");
        readonly List<EndfieldCharacterShadow> groups = new List<EndfieldCharacterShadow>(MaxGroups);
        readonly List<Bounds> bounds = new List<Bounds>(MaxGroups);
        readonly Matrix4x4[] matrices = new Matrix4x4[MaxGroups];
        readonly Vector4[] rectangles = new Vector4[MaxGroups];
        readonly Vector4[] parameters = new Vector4[MaxGroups];
        readonly Vector4[] filterRadii = new Vector4[MaxGroups];
        readonly Vector4[] lightDirections = new Vector4[MaxGroups];

        public override void Execute(EndfieldFrameData frame)
        {
            groups.Clear(); bounds.Clear();
            var command = frame.command;
            command.SetGlobalInt("_CharacterShadowCount", 0);
            command.SetGlobalTexture(atlas, SystemInfo.usesReversedZBuffer ? Texture2D.blackTexture : Texture2D.whiteTexture);
            foreach (var group in EndfieldCharacterShadow.Active) if (group) group.SetReceiverIndex(-1);
            if (frame.mainLightIndex < 0) return;
            var visible = frame.culling.visibleLights[frame.mainLightIndex];
            Light light = visible.light;
            if (light.shadows == LightShadows.None || light.shadowStrength <= 0) return;

            int tileResolution = 128;
            int guard = 2;
            foreach (var group in EndfieldCharacterShadow.Active)
            {
                if (!group || !group.isActiveAndEnabled || groups.Count >= MaxGroups || !group.TryGetCasterBounds(out Bounds box)) continue;
                groups.Add(group); bounds.Add(box);
                tileResolution = Mathf.Max(tileResolution, Mathf.NextPowerOfTwo(Mathf.Clamp(group.resolution, 128, 2048)));
                float maximumRadius = group.filterRadiusTexels / Mathf.Min(1, Mathf.Max(.25f, group.filterAspectRatio));
                guard = Mathf.Max(guard, Mathf.CeilToInt(maximumRadius) + 2);
            }
            if (groups.Count == 0) return;

            // 图集按2:1打包容量；每组的实际X/Y过滤像素范围独立传参，避免绑定某个截帧的布局。
            int columns = Mathf.NextPowerOfTwo(Mathf.CeilToInt(Mathf.Sqrt(groups.Count * 2)));
            int rows = columns / 2;
            int usableResolution = Mathf.Min(tileResolution, SystemInfo.maxTextureSize / columns - 2 * guard);
            tileResolution = usableResolution + 2 * guard;
            int width = columns * tileResolution, height = rows * tileResolution;
            // 源372为D16，逻辑raster bias8在reverse-Z平台成为native -8个D16单位。
            command.GetTemporaryRT(atlas, new RenderTextureDescriptor(width, height)
                { graphicsFormat = GraphicsFormat.None, depthStencilFormat = GraphicsFormat.D16_UNorm,
                    shadowSamplingMode = ShadowSamplingMode.RawDepth, msaaSamples = 1 }, FilterMode.Point);
            frame.targets.RegisterEffect(atlas);
            command.SetRenderTarget(new RenderTargetIdentifier(atlas));
            command.SetViewport(new Rect(0, 0, width, height));
            command.ClearRenderTarget(RTClearFlags.Depth, Color.clear, 1, 0);
            frame.Flush();

            Vector3 towardLight = -visible.localToWorldMatrix.GetColumn(2);
            Quaternion rotation = light.transform.rotation;
            for (int index = 0; index < groups.Count; index++)
            {
                var group = groups[index];
                FitProjection(bounds[index], rotation, light.shadowNearPlane, usableResolution, group,
                    out Matrix4x4 view, out Matrix4x4 projection);
                int x = index % columns * tileResolution + guard;
                int y = index / columns * tileResolution + guard;
                Matrix4x4 tile = Matrix4x4.identity;
                tile.m00 = usableResolution / (float)width; tile.m11 = usableResolution / (float)height;
                tile.m03 = x / (float)width; tile.m13 = y / (float)height;
                matrices[index] = tile * EndfieldShadowUtils.AtlasMatrix(projection, view, 0, 1);
                rectangles[index] = new Vector4(x / (float)width, y / (float)height,
                    (x + usableResolution) / (float)width, (y + usableResolution) / (float)height);
                // 源188.z是投影X梯度的倒数，不是max(X,Y) texel。
                Vector3 rowX = new Vector3(matrices[index].m00, matrices[index].m01, matrices[index].m02);
                float worldTexelX = 1 / (rowX.magnitude * width);
                parameters[index] = new Vector4(group.strength * light.shadowStrength, worldTexelX, group.depthBiasTexels, group.normalBiasTexels);
                filterRadii[index] = new Vector4(group.filterRadiusTexels,
                    group.filterRadiusTexels / Mathf.Max(.25f, group.filterAspectRatio), 0, 0);
                lightDirections[index] = new Vector4(towardLight.x, towardLight.y, towardLight.z, 0);
                group.SetReceiverIndex(index);

                command.SetViewport(new Rect(x, y, usableResolution, usableResolution));
                command.SetViewProjectionMatrices(view, projection);
                // 源372是position-only、CullOff，没有顶点N偏移；接收端单独实施3/6 texel。
                command.SetGlobalVector("_ShadowBias", Vector4.zero);
                command.SetGlobalDepthBias(group.rasterDepthBias, 0);
                foreach (Renderer caster in group.casters)
                {
                    if (!EndfieldCharacterShadow.IsCaster(caster)) continue;
                    Material[] materials = caster.sharedMaterials;
                    for (int submesh = 0; submesh < materials.Length; submesh++)
                    {
                        Material material = materials[submesh];
                        if (!material) continue;
                        int pass = material.FindPass("CharacterShadowCaster");
                        if (pass >= 0) command.DrawRenderer(caster, material, submesh, pass);
                    }
                }
                frame.Flush();
            }
            command.SetGlobalDepthBias(0, 0);
            command.SetGlobalTexture(atlas, new RenderTargetIdentifier(atlas), RenderTextureSubElement.Depth);
            command.SetGlobalMatrixArray("_CharacterWorldToShadow", matrices);
            command.SetGlobalVectorArray("_CharacterShadowRects", rectangles);
            command.SetGlobalVectorArray("_CharacterShadowParams", parameters);
            command.SetGlobalVectorArray("_CharacterShadowFilterRadii", filterRadii);
            command.SetGlobalVectorArray("_CharacterShadowLightDirections", lightDirections);
            command.SetGlobalVector("_CharacterShadowAtlasSize", new Vector4(1f / width, 1f / height, width, height));
            command.SetGlobalInt("_CharacterShadowCount", groups.Count);
            frame.Flush();
        }

        static void FitProjection(Bounds bounds, Quaternion lightRotation, float nearPlane, int resolution,
            EndfieldCharacterShadow group, out Matrix4x4 view, out Matrix4x4 projection)
        {
            float near = Mathf.Max(.001f, nearPlane);
            Vector3 cameraPosition = bounds.center - lightRotation * Vector3.forward * (bounds.extents.magnitude + near);
            view = Matrix4x4.Scale(new Vector3(1, 1, -1)) * Matrix4x4.TRS(cameraPosition, lightRotation, Vector3.one).inverse;
            Vector3 minimum = new Vector3(float.PositiveInfinity, float.PositiveInfinity, float.PositiveInfinity);
            Vector3 maximum = new Vector3(float.NegativeInfinity, float.NegativeInfinity, float.NegativeInfinity);
            for (int corner = 0; corner < 8; corner++)
            {
                Vector3 point = bounds.center + Vector3.Scale(bounds.extents,
                    new Vector3((corner & 1) == 0 ? -1 : 1, (corner & 2) == 0 ? -1 : 1, (corner & 4) == 0 ? -1 : 1));
                point = view.MultiplyPoint3x4(point);
                minimum = Vector3.Min(minimum, point); maximum = Vector3.Max(maximum, point);
            }
            float spanX = Mathf.Max(maximum.x - minimum.x, .001f);
            float spanY = Mathf.Max(maximum.y - minimum.y, .001f);
            float padding = (group.depthBiasTexels + group.normalBiasTexels) * spanX / resolution
                + (group.filterRadiusTexels + 1) * Mathf.Max(spanX, spanY) / resolution;
            projection = Matrix4x4.Ortho(minimum.x - padding, maximum.x + padding, minimum.y - padding, maximum.y + padding,
                Mathf.Max(.001f, -maximum.z - padding), Mathf.Max(near + .001f, -minimum.z + padding));
        }
    }
}
