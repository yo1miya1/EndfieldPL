using System;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;
using Endfield.Rendering;

namespace Endfield.Editor
{
    /// <summary>直接渲染真实编辑器场景，不依赖屏幕操作；PNG 与 RDC 使用同一相机、尺寸和绘制。</summary>
    public static class EndfieldFrameCapture
    {
        [Serializable]
        sealed class Evidence
        {
            public string source = "Unity Editor Camera.Render; actual scene and active SRP";
            public string utc, scene, cameraType, graphicsDevice, graphicsApi, pipeline, png, rdc, rdcSha256;
            public int width, height, warmupFrames;
            public Vector3 cameraPosition;
            public Quaternion cameraRotation;
            public Matrix4x4 view, projection;
            public bool renderDocRequested;
        }

        public static string Capture(EndfieldEditorBridge.Request request)
        {
            var referenceCamera = Camera.main;
            if (!referenceCamera) throw new InvalidOperationException("The loaded scene has no MainCamera.");
            bool sceneViewRequest = request.argument != null && request.argument.StartsWith("scene-");
            var sceneView = sceneViewRequest ? (SceneView.lastActiveSceneView ?? EditorWindow.GetWindow<SceneView>()) : null;
            var camera = sceneViewRequest ? sceneView.camera : referenceCamera;
            var cameraSettings = camera.GetComponent<EndfieldCameraSettings>();
            bool temporarySettings = !cameraSettings;
            if (temporarySettings) cameraSettings = camera.gameObject.AddComponent<EndfieldCameraSettings>();
            bool previousPost = cameraSettings.enablePostProcessing;
            if (request.argument == "scene-no-post" || request.disablePostProcessing) cameraSettings.enablePostProcessing = false;
            bool previousOverride = cameraSettings && cameraSettings.overrideDebugView;
            var previousDebug = cameraSettings ? cameraSettings.debugView : EndfieldDebugView.Final;
            if (cameraSettings && request.argument != null && request.argument.StartsWith("debug:"))
            {
                cameraSettings.overrideDebugView = true;
                cameraSettings.debugView = (EndfieldDebugView)Enum.Parse(typeof(EndfieldDebugView), request.argument.Substring(6));
            }
            if (!string.IsNullOrEmpty(request.debugView))
            {
                cameraSettings.overrideDebugView = true;
                cameraSettings.debugView = (EndfieldDebugView)Enum.Parse(typeof(EndfieldDebugView), request.debugView);
            }
            Vector3 savedPosition = camera.transform.position;
            Quaternion savedRotation = camera.transform.rotation;
            float savedFieldOfView = camera.fieldOfView, savedNear = camera.nearClipPlane, savedFar = camera.farClipPlane;
            if (sceneViewRequest && request.argument != "scene-current")
            {
                cameraSettings.ResetTemporalHistory();
                camera.transform.SetPositionAndRotation(referenceCamera.transform.position, referenceCamera.transform.rotation);
                camera.fieldOfView = referenceCamera.fieldOfView;
                camera.nearClipPlane = referenceCamera.nearClipPlane;
                camera.farClipPlane = referenceCamera.farClipPlane;
            }
            if (request.overrideCamera)
            {
                cameraSettings.ResetTemporalHistory();
                camera.transform.SetPositionAndRotation(request.cameraPosition,
                    Quaternion.LookRotation(request.cameraTarget - request.cameraPosition, Vector3.up));
                camera.fieldOfView = request.fieldOfView;
                camera.nearClipPlane = 0.01f;
            }
            if (request.width < 16 || request.height < 16 || request.width > 8192 || request.height > 8192)
                throw new ArgumentException("Invalid capture dimensions.");
            string folder = Path.Combine(EndfieldEditorBridge.OutputRoot, "captures",
                DateTime.UtcNow.ToString("yyyyMMdd-HHmmss-fff"));
            Directory.CreateDirectory(folder);
            var target = new RenderTexture(request.width, request.height, 24, RenderTextureFormat.ARGB32,
                RenderTextureReadWrite.sRGB) { name = "Editor verification output", antiAliasing = 1 };
            target.Create();
            var previousTarget = camera.targetTexture;
            var previousActive = RenderTexture.active;
            string rdc = null;
            Texture2D image = null;
            var lights = request.disableShadows || request.disableAdditionalLights ? UnityEngine.Object.FindObjectsByType<Light>(FindObjectsSortMode.None) : Array.Empty<Light>();
            var savedShadows = lights.Select(light => light.shadows).ToArray();
            var savedLightEnabled = lights.Select(light => light.enabled).ToArray();
            try
            {
                foreach (var light in lights)
                {
                    if (request.disableShadows) light.shadows = LightShadows.None;
                    if (request.disableAdditionalLights && light != RenderSettings.sun) light.enabled = false;
                }
                camera.targetTexture = target;
                camera.aspect = (float)request.width / request.height;
                // 时序抗锯齿需要真实连续渲染来建立历史，不能把单帧离屏截图当作稳定画面。
                int warmupFrames = Mathf.Clamp(request.warmupFrames, 1, 64);
                for (int frame = 0; frame < warmupFrames; frame++) camera.Render();
                RenderTexture.active = target;
                image = new Texture2D(target.width, target.height, TextureFormat.RGBA32, false, true);
                // Camera.Render会提交给独立渲染线程。同步回读使RenderDoc起止点包住完整GPU帧，
                // 否则主线程提前EndCapture会随机只截到Bloom尾部或前一帧。
                image.ReadPixels(new Rect(0, 0, target.width, target.height), 0, 0);
                if (request.renderDoc) NativeRenderDoc.Begin(Path.Combine(folder, "editor"));
                try
                {
                    camera.Render();
                    RenderTexture.active = target;
                    image.ReadPixels(new Rect(0, 0, target.width, target.height), 0, 0);
                }
                finally { if (request.renderDoc) rdc = NativeRenderDoc.End(); }
                image.Apply(false, false);
                string png = Path.Combine(folder, "editor-camera.png");
                File.WriteAllBytes(png, image.EncodeToPNG());
                var evidence = new Evidence
                {
                    utc = DateTime.UtcNow.ToString("O"), scene = referenceCamera.gameObject.scene.path,
                    cameraType = camera.cameraType.ToString(),
                    graphicsDevice = SystemInfo.graphicsDeviceName, graphicsApi = SystemInfo.graphicsDeviceType.ToString(),
                    pipeline = GraphicsSettings.currentRenderPipeline ? GraphicsSettings.currentRenderPipeline.GetType().FullName : "Built-in",
                    width = target.width, height = target.height, cameraPosition = camera.transform.position,
                    warmupFrames = warmupFrames,
                    cameraRotation = camera.transform.rotation, view = camera.worldToCameraMatrix,
                    projection = camera.projectionMatrix, png = png, rdc = rdc,
                    renderDocRequested = request.renderDoc, rdcSha256 = rdc == null ? null : Hash(rdc)
                };
                File.WriteAllText(Path.Combine(folder, "evidence.json"), JsonUtility.ToJson(evidence, true));
                return folder;
            }
            finally
            {
                for (int i = 0; i < lights.Length; i++) if (lights[i])
                {
                    lights[i].shadows = savedShadows[i];
                    lights[i].enabled = savedLightEnabled[i];
                }
                camera.targetTexture = previousTarget;
                // 场景相机由Unity管理视口比例；结束比较后恢复自动比例，避免截图尺寸固定Game视口。
                camera.ResetAspect();
                if (cameraSettings)
                {
                    cameraSettings.overrideDebugView = previousOverride;
                    cameraSettings.debugView = previousDebug;
                    cameraSettings.enablePostProcessing = previousPost;
                    if (temporarySettings) UnityEngine.Object.DestroyImmediate(cameraSettings);
                }
                if (sceneViewRequest || request.overrideCamera)
                {
                    camera.transform.SetPositionAndRotation(savedPosition, savedRotation);
                    camera.fieldOfView = savedFieldOfView;
                    camera.nearClipPlane = savedNear;
                    camera.farClipPlane = savedFar;
                    if (cameraSettings) cameraSettings.ResetTemporalHistory();
                }
                RenderTexture.active = previousActive;
                if (image) UnityEngine.Object.DestroyImmediate(image);
                target.Release();
                UnityEngine.Object.DestroyImmediate(target);
            }
        }

        static string Hash(string file)
        {
            using (var stream = File.OpenRead(file))
            using (var hash = SHA256.Create())
                return BitConverter.ToString(hash.ComputeHash(stream)).Replace("-", "").ToLowerInvariant();
        }

        // RenderDoc 官方稳定 app API 1.6.0；仅编辑器诊断使用，不进入游戏运行时。
        static class NativeRenderDoc
        {
            [DllImport("renderdoc", CallingConvention = CallingConvention.Cdecl)]
            static extern int RENDERDOC_GetAPI(int version, out IntPtr api);
            [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate void SetPath([MarshalAs(UnmanagedType.LPStr)] string path);
            [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate uint GetCount();
            [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate void StartCapture(IntPtr device, IntPtr window);
            [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate uint EndCapture(IntPtr device, IntPtr window);
            [UnmanagedFunctionPointer(CallingConvention.Cdecl)] delegate uint GetCapture(uint index, IntPtr path, ref uint length, out ulong timestamp);
            static IntPtr api;
            static uint previousCount;
            static string outputPrefix;
            static T Function<T>(int slot) where T : Delegate =>
                Marshal.GetDelegateForFunctionPointer<T>(Marshal.ReadIntPtr(api, slot * IntPtr.Size));

            public static void Begin(string prefix)
            {
                if (RENDERDOC_GetAPI(10600, out api) != 1)
                    throw new InvalidOperationException("RenderDoc app API unavailable; start Unity with -load-renderdoc.");
                if (Function<GetCount>(20)() != 0) throw new InvalidOperationException("Another RenderDoc capture is active.");
                outputPrefix = Path.GetFullPath(prefix);
                previousCount = Function<GetCount>(13)();
                Function<SetPath>(11)(outputPrefix);
                Function<StartCapture>(19)(IntPtr.Zero, IntPtr.Zero);
                if (Function<GetCount>(20)() == 0) throw new InvalidOperationException("RenderDoc did not start capture.");
            }

            public static string End()
            {
                if (Function<EndCapture>(21)(IntPtr.Zero, IntPtr.Zero) == 0)
                    throw new InvalidOperationException("RenderDoc capture failed.");
                uint count = Function<GetCount>(13)();
                if (count <= previousCount) throw new IOException("No newly completed RenderDoc capture.");
                var get = Function<GetCapture>(14);
                uint length = 0;
                if (get(count - 1, IntPtr.Zero, ref length, out _) == 0 || length == 0 || length > 32768)
                    throw new IOException("Invalid RenderDoc capture filename.");
                IntPtr buffer = Marshal.AllocHGlobal((int)length + 1);
                try
                {
                    if (get(count - 1, buffer, ref length, out _) == 0) throw new IOException("Could not read RenderDoc filename.");
                    string file = Path.GetFullPath(Marshal.PtrToStringUTF8(buffer));
                    if (!file.StartsWith(outputPrefix, StringComparison.OrdinalIgnoreCase) || !File.Exists(file))
                        throw new IOException("Completed capture does not belong to this request.");
                    return file;
                }
                finally { Marshal.FreeHGlobal(buffer); }
            }
        }
    }
}
