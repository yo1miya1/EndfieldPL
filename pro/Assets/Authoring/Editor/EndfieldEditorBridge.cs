using System;
using System.IO;
using System.Linq;
using System.Reflection;
using UnityEditor;
using UnityEngine;

namespace Endfield.Editor
{
    /// <summary>
    /// 只在编辑器运行的文件命令入口。命令与回执保存在工作区 tmp，运行构建不包含它。
    /// 外部程序先写临时文件再原子重命名为 .request.json；每个请求只执行一次。
    /// </summary>
    [InitializeOnLoad]
    public static class EndfieldEditorBridge
    {
        public static string Workspace => Path.GetFullPath(Path.Combine(Application.dataPath, "../.."));
        public static string OutputRoot => Path.Combine(Workspace, "tmp", "unity");
        static double nextPoll;
        static bool busy;

        [Serializable]
        public sealed class Request
        {
            public string id;
            public string action;
            public string argument;
            public int width = 1920;
            public int height = 1080;
            public bool renderDoc;
            public int warmupFrames = 16;
            public bool overrideCamera;
            public Vector3 cameraPosition;
            public Vector3 cameraTarget;
            public float fieldOfView = 30;
            public string debugView;
            public bool disablePostProcessing;
            public bool disableShadows;
            public bool disableAdditionalLights;
        }

        [Serializable]
        public sealed class Result
        {
            public string id;
            public string action;
            public bool success;
            public string detail;
            public string utc;
        }

        static EndfieldEditorBridge()
        {
            EditorApplication.update += Poll;
        }

        static void Poll()
        {
            if (busy || EditorApplication.isCompiling || EditorApplication.isUpdating ||
                EditorApplication.timeSinceStartup < nextPoll) return;
            nextPoll = EditorApplication.timeSinceStartup + 0.5;
            string directory = Path.Combine(OutputRoot, "commands");
            Directory.CreateDirectory(directory);
            var candidate = Directory.GetFiles(directory, "*.request.json").OrderBy(x => x).FirstOrDefault();
            if (candidate == null) return;
            string running = candidate.Replace(".request.json", ".running.json");
            File.Move(candidate, running);
            busy = true;
            Request request = null;
            var result = new Result { utc = DateTime.UtcNow.ToString("O") };
            try
            {
                request = JsonUtility.FromJson<Request>(File.ReadAllText(running));
                result.id = request.id;
                result.action = request.action;
                switch (request.action)
                {
                    case "refresh":
                        AssetDatabase.Refresh(ImportAssetOptions.ForceSynchronousImport);
                        result.detail = "AssetDatabase refresh completed; inspect subsequent compilation separately.";
                        break;
                    case "invoke":
                        // 明确的 Type.Method，不执行任意表达式；参数为空的公开静态命令才可调用。
                        Invoke(request.argument);
                        result.detail = request.argument;
                        break;
                    case "open-scene":
                        UnityEditor.SceneManagement.EditorSceneManager.OpenScene(request.argument,
                            UnityEditor.SceneManagement.OpenSceneMode.Single);
                        result.detail = request.argument;
                        break;
                    case "capture":
                        result.detail = EndfieldFrameCapture.Capture(request);
                        break;
                    case "quit":
                        result.detail = "Editor exit requested after writing this receipt.";
                        break;
                    default: throw new ArgumentException("Unknown editor action: " + request.action);
                }
                result.success = true;
            }
            catch (Exception exception)
            {
                result.success = false;
                result.detail = exception.ToString();
                Debug.LogException(exception);
            }
            finally
            {
                File.WriteAllText(running.Replace(".running.json", ".result.json"), JsonUtility.ToJson(result, true));
                busy = false;
            }
            // 后台编辑器不一定触发下一轮delayCall；先落盘回执，再在本次update直接退出。
            if (result.success && request.action == "quit") EditorApplication.Exit(0);
        }

        static void Invoke(string name)
        {
            int separator = name.LastIndexOf('.');
            if (separator <= 0) throw new ArgumentException("Expected full Type.Method name.");
            string typeName = name.Substring(0, separator);
            var type = AppDomain.CurrentDomain.GetAssemblies().Select(x => x.GetType(typeName)).FirstOrDefault(x => x != null);
            var method = type?.GetMethod(name.Substring(separator + 1), BindingFlags.Public | BindingFlags.Static,
                null, Type.EmptyTypes, null);
            if (method == null) throw new MissingMethodException(name);
            method.Invoke(null, null);
        }
    }
}
