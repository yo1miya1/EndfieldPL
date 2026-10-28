using UnityEngine;
using UnityEngine.Rendering;

namespace Endfield.Rendering
{
    internal sealed class EndfieldLightingPass : EndfieldRenderPass
    {
        public override string Name => "Lighting";
        readonly Vector4[] positions = new Vector4[32];
        readonly Vector4[] colors = new Vector4[32];
        readonly Vector4[] spotDirections = new Vector4[32];
        readonly Vector4[] spotAngles = new Vector4[32];

        public override void Execute(EndfieldFrameData frame)
        {
            Vector4 mainDirection = new Vector4(0, 1, 0, 0);
            Vector4 mainColor = Vector4.zero;
            if (frame.mainLightIndex >= 0)
            {
                var main = frame.culling.visibleLights[frame.mainLightIndex];
                mainDirection = -main.localToWorldMatrix.GetColumn(2);
                mainDirection.w = 0;
                mainColor = main.finalColor;
            }
            frame.command.SetGlobalVector("_MainLightDirection", mainDirection);
            frame.command.SetGlobalVector("_MainLightColor", mainColor);
            int lightCount = 0;
            var visibleLights = frame.culling.visibleLights;
            for (int index = 0; index < visibleLights.Length; index++)
            {
                var visible = visibleLights[index];
                if (lightCount >= Mathf.Clamp(frame.settings.maxAdditionalLights, 0, 32)) break;
                if (index == frame.mainLightIndex) continue;
                bool directional = visible.lightType == LightType.Directional;
                if (!directional && visible.lightType != LightType.Point && visible.lightType != LightType.Spot) continue;
                // 和Unity light convention一致：方向光xyz为toward-light，w=0；局部光w为逆范围平方。
                Vector4 position = directional ? -visible.localToWorldMatrix.GetColumn(2) : visible.localToWorldMatrix.GetColumn(3);
                position.w = directional ? 0 : 1f / Mathf.Max(visible.range * visible.range, .0001f);
                positions[lightCount] = position;
                colors[lightCount] = visible.finalColor;
                spotDirections[lightCount] = visible.localToWorldMatrix.GetColumn(2);
                if (visible.lightType == LightType.Spot)
                {
                    float outerCos = Mathf.Cos(visible.spotAngle * .5f * Mathf.Deg2Rad);
                    float innerCos = Mathf.Cos(visible.light.innerSpotAngle * .5f * Mathf.Deg2Rad);
                    float inverseRange = 1f / Mathf.Max(innerCos - outerCos, .001f);
                    spotAngles[lightCount] = new Vector4(inverseRange, -outerCos * inverseRange, 0, 0);
                }
                else spotAngles[lightCount] = new Vector4(0, 1, 0, 0);
                lightCount++;
            }
            frame.command.SetGlobalInt("_AdditionalLightCount", lightCount);
            frame.command.SetGlobalVectorArray("_AdditionalLightPositions", positions);
            frame.command.SetGlobalVectorArray("_AdditionalLightColors", colors);
            frame.command.SetGlobalVectorArray("_AdditionalLightSpotDirections", spotDirections);
            frame.command.SetGlobalVectorArray("_AdditionalLightSpotAngles", spotAngles);
            // 全屏阶段没有逐Renderer的UnityPerDraw，单独传Unity环境探针的标准SH9。
            var ambient = new SHCoefficients(RenderSettings.ambientProbe);
            frame.command.SetGlobalVector("_AmbientSHAr", ambient.SHAr);
            frame.command.SetGlobalVector("_AmbientSHAg", ambient.SHAg);
            frame.command.SetGlobalVector("_AmbientSHAb", ambient.SHAb);
            frame.command.SetGlobalVector("_AmbientSHBr", ambient.SHBr);
            frame.command.SetGlobalVector("_AmbientSHBg", ambient.SHBg);
            frame.command.SetGlobalVector("_AmbientSHBb", ambient.SHBb);
            frame.command.SetGlobalVector("_AmbientSHC", ambient.SHC);
            frame.command.SetRenderTarget(frame.targets.sceneColor);
            frame.command.ClearRenderTarget(false, true, frame.camera.backgroundColor.linear);
            Fullscreen(frame, frame.lightingMaterial, 0);
            frame.Flush();
            // 源角色有自己的表面受光公式；保留其GBuffer payload，深度相等时重绘可见表面。
            // 这仍属于Lighting阶段，材料自己决定是否提供此Pass，不按角色名分支。
            frame.command.SetRenderTarget(new RenderTargetIdentifier(frame.targets.sceneColor), new RenderTargetIdentifier(frame.targets.depthAttachment));
            frame.Flush();
            DrawGeometry(frame, "EndfieldSurfaceLighting", RenderQueueRange.opaque, SortingCriteria.CommonOpaque);
            // 写深度的不透明特效仍按opaque顺序绘制，不强行放进透明队列。
            DrawGeometry(frame, "EndfieldEffect", RenderQueueRange.opaque, SortingCriteria.CommonOpaque);
        }
    }
}
