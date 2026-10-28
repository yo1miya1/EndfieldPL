using System;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace Endfield.Editor
{
    /// <summary>读取真正Game视口的已渲染纹理，区别于给Camera临时绑定RenderTexture。</summary>
    public static class EndfieldGameViewCapture
    {
        static EditorWindow pendingView;
        static double captureAfter;

        public static void CaptureCurrentGameView()
        {
            Type type = typeof(EditorWindow).Assembly.GetType("UnityEditor.GameView");
            pendingView = Resources.FindObjectsOfTypeAll(type).Cast<EditorWindow>().First();
            captureAfter = EditorApplication.timeSinceStartup + 2;
            EditorApplication.update -= ReadAfterRepaint;
            EditorApplication.update += ReadAfterRepaint;
            pendingView.Repaint();
            EditorApplication.QueuePlayerLoopUpdate();
        }

        static void ReadAfterRepaint()
        {
            pendingView.Repaint();
            EditorApplication.QueuePlayerLoopUpdate();
            if (EditorApplication.timeSinceStartup < captureAfter) return;
            EditorApplication.update -= ReadAfterRepaint;
            var field = pendingView.GetType().GetField("m_RenderTexture", BindingFlags.Instance | BindingFlags.NonPublic);
            var rendered = (RenderTexture)field.GetValue(pendingView);
            string folder = Path.Combine(EndfieldEditorBridge.OutputRoot, "game-view", DateTime.UtcNow.ToString("yyyyMMdd-HHmmss-fff"));
            Directory.CreateDirectory(folder);
            var previous = RenderTexture.active;
            var image = new Texture2D(rendered.width, rendered.height, TextureFormat.RGBA32, false, true);
            try
            {
                RenderTexture.active = rendered;
                image.ReadPixels(new Rect(0, 0, rendered.width, rendered.height), 0, 0);
                image.Apply(false, false);
                File.WriteAllBytes(Path.Combine(folder, "game-view.png"), image.EncodeToPNG());
                File.WriteAllText(Path.Combine(folder, "evidence.txt"),
                    "Source: Unity GameView.m_RenderTexture after native GameView repaint; no Camera.Render or camera target replacement.\n" +
                    "Camera targetTexture is null: " + (Camera.main.targetTexture == null) + "\n" +
                    "Resolution: " + rendered.width + " x " + rendered.height + "\n" +
                    "Scene: " + Camera.main.gameObject.scene.path + "\n");
                File.WriteAllText(Path.Combine(EndfieldEditorBridge.OutputRoot, "latest-game-view.txt"), folder);
            }
            finally { RenderTexture.active = previous; UnityEngine.Object.DestroyImmediate(image); pendingView = null; }
        }

        public static void InspectViewTexture()
        {
            Type type = typeof(EditorWindow).Assembly.GetType("UnityEditor.GameView");
            var view = Resources.FindObjectsOfTypeAll(type).FirstOrDefault();
            if (!view) throw new InvalidOperationException("No open Unity GameView.");
            var report = new System.Text.StringBuilder();
            for (Type current = type; current != null; current = current.BaseType)
            {
                var flags = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly;
                foreach (var field in current.GetFields(flags))
                    if (typeof(Texture).IsAssignableFrom(field.FieldType))
                        report.AppendLine(current.Name + "." + field.Name + ": " + field.GetValue(view));
                foreach (var property in current.GetProperties(flags))
                    if (typeof(Texture).IsAssignableFrom(property.PropertyType) && property.GetIndexParameters().Length == 0)
                        report.AppendLine(current.Name + "." + property.Name + ": " + property.GetValue(view));
            }
            File.WriteAllText(Path.Combine(EndfieldEditorBridge.OutputRoot, "game-view-texture.txt"), report.ToString());
        }
    }
}
