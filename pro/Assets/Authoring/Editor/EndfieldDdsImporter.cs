using System;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.Experimental.Rendering;

namespace Endfield.Authoring
{
    /// <summary>DDS原生像素发布：保留压缩块、SRV颜色格式和完整mip，不经PNG或平均降采样。</summary>
    public static class EndfieldDdsImporter
    {
        // dds相对本JSON所在目录；viewFormat表示实际SRV，省略时采用DX10头中的格式。
        [Serializable] public sealed class Import { public string dds, viewFormat; }

        sealed class Header
        {
            public byte[] bytes;
            public int width, height, mipCount, offset;
            public bool cube;
            public GraphicsFormat format;
        }

        public static string GetSourcePath(string importPath)
        {
            var plan = JsonUtility.FromJson<Import>(File.ReadAllText(importPath));
            return Path.GetFullPath(Path.Combine(Path.GetDirectoryName(importPath), plan.dds));
        }

        public static Texture2D LoadFromImport(string importPath)
        {
            var plan = JsonUtility.FromJson<Import>(File.ReadAllText(importPath));
            return LoadTexture(Path.Combine(Path.GetDirectoryName(importPath), plan.dds), plan.viewFormat);
        }

        public static Texture2D LoadTexture(string sourceDds, string viewFormat = null)
        {
            Header source = ReadHeader(sourceDds, viewFormat);
            if (source.cube) throw new InvalidDataException("A cubemap requires LoadCubemapFromImport: " + sourceDds);
            var texture = new Texture2D(source.width, source.height, source.format, source.mipCount,
                source.mipCount > 1 ? TextureCreationFlags.MipChain : TextureCreationFlags.None);
            Upload(texture, source);
            return texture;
        }

        // UI和材质共用此入口；各采样方式可发布到不同asset，避免共享纹理相互改wrap。
        public static Texture2D LoadOrCreate(string sourceDds, string outputAssetPath,
            string wrapU = "Repeat", string wrapV = "Repeat", string filter = "Bilinear", string viewFormat = null)
        {
            Header source = ReadHeader(sourceDds, viewFormat);
            if (source.cube) throw new InvalidDataException("Expected Texture2D DDS: " + sourceDds);
            return PublishTexture(source, outputAssetPath, wrapU, wrapV, filter);
        }

        // 材质槽也可接收原生Cubemap，例如环境几何使用的独立Cube，不局限全局ReflectionProbe。
        public static Texture LoadAssetFromImport(string importPath, string outputAssetPath,
            string wrapU = "Repeat", string wrapV = "Repeat", string filter = "Bilinear")
        {
            var plan = JsonUtility.FromJson<Import>(File.ReadAllText(importPath));
            Header source = ReadHeader(Path.Combine(Path.GetDirectoryName(importPath), plan.dds), plan.viewFormat);
            if (source.cube) return PublishCubemap(source, outputAssetPath);
            return PublishTexture(source, outputAssetPath, wrapU, wrapV, filter);
        }

        static Texture2D PublishTexture(Header source, string outputAssetPath, string wrapU, string wrapV, string filter)
        {
            var texture = AssetDatabase.LoadAssetAtPath<Texture2D>(outputAssetPath);
            if (!texture)
            {
                texture = new Texture2D(source.width, source.height, source.format, source.mipCount,
                    source.mipCount > 1 ? TextureCreationFlags.MipChain : TextureCreationFlags.None);
                AssetDatabase.CreateAsset(texture, outputAssetPath);
            }
            else texture.Reinitialize(source.width, source.height, source.format, source.mipCount > 1);
            Upload(texture, source);
            texture.name = Path.GetFileNameWithoutExtension(outputAssetPath);
            texture.wrapModeU = (TextureWrapMode)Enum.Parse(typeof(TextureWrapMode), wrapU);
            texture.wrapModeV = (TextureWrapMode)Enum.Parse(typeof(TextureWrapMode), wrapV);
            texture.filterMode = (FilterMode)Enum.Parse(typeof(FilterMode), filter);
            EditorUtility.SetDirty(texture);
            return texture;
        }

        public static Cubemap LoadCubemapFromImport(string importPath, string outputAssetPath)
        {
            var plan = JsonUtility.FromJson<Import>(File.ReadAllText(importPath));
            Header source = ReadHeader(Path.Combine(Path.GetDirectoryName(importPath), plan.dds), plan.viewFormat);
            if (!source.cube) throw new InvalidDataException("Expected cubemap DDS: " + importPath);
            return PublishCubemap(source, outputAssetPath);
        }

        static Cubemap PublishCubemap(Header source, string outputAssetPath)
        {
            var cube = AssetDatabase.LoadAssetAtPath<Cubemap>(outputAssetPath);
            if (!cube)
            {
                cube = new Cubemap(source.width, source.format,
                    source.mipCount > 1 ? TextureCreationFlags.MipChain : TextureCreationFlags.None, source.mipCount);
                AssetDatabase.CreateAsset(cube, outputAssetPath);
            }
            // DDS的cube存储是face0 mip0..N、face1 mip0..N；保留源face顺序与每级块。
            int offset = source.offset;
            for (int face = 0; face < 6; face++)
                for (int mip = 0; mip < source.mipCount; mip++)
                {
                    cube.SetPixelData(source.bytes, mip, (CubemapFace)face, offset);
                    offset += MipBytes(source, mip);
                }
            cube.Apply(false, false);
            cube.name = Path.GetFileNameWithoutExtension(outputAssetPath);
            cube.wrapMode = TextureWrapMode.Clamp;
            cube.filterMode = FilterMode.Trilinear;
            EditorUtility.SetDirty(cube);
            return cube;
        }

        static void Upload(Texture2D texture, Header source)
        {
            int length = 0;
            for (int mip = 0; mip < source.mipCount; mip++) length += MipBytes(source, mip);
            var payload = new byte[length];
            Buffer.BlockCopy(source.bytes, source.offset, payload, 0, length);
            texture.LoadRawTextureData(payload);
            texture.Apply(false, false);
        }

        static int MipBytes(Header source, int mip)
        {
            int width = Mathf.Max(1, source.width >> mip), height = Mathf.Max(1, source.height >> mip);
            int blockWidth = (int)GraphicsFormatUtility.GetBlockWidth(source.format);
            int blockHeight = (int)GraphicsFormatUtility.GetBlockHeight(source.format);
            return ((width + blockWidth - 1) / blockWidth) * ((height + blockHeight - 1) / blockHeight)
                * (int)GraphicsFormatUtility.GetBlockSize(source.format);
        }

        static Header ReadHeader(string path, string viewFormat)
        {
            byte[] bytes = File.ReadAllBytes(path);
            using var reader = new BinaryReader(new MemoryStream(bytes, false));
            if (reader.ReadUInt32() != 0x20534444 || reader.ReadUInt32() != 124)
                throw new InvalidDataException("Not a DDS file: " + path);
            reader.BaseStream.Position = 12;
            int height = reader.ReadInt32(), width = reader.ReadInt32();
            reader.BaseStream.Position = 28;
            int mips = Mathf.Max(1, reader.ReadInt32());
            reader.BaseStream.Position = 84;
            uint fourCC = reader.ReadUInt32();
            reader.BaseStream.Position = 112;
            bool cube = (reader.ReadUInt32() & 0x200) != 0;
            GraphicsFormat format;
            int offset = 128;
            if (fourCC == 0x30315844) // DX10
            {
                reader.BaseStream.Position = 128;
                uint dxgi = reader.ReadUInt32();
                uint dimension = reader.ReadUInt32();
                cube = (reader.ReadUInt32() & 4) != 0;
                uint arraySize = reader.ReadUInt32();
                if (dimension != 3 || arraySize != 1)
                    throw new NotSupportedException("DDS importer accepts one Texture2D or one cubemap, not volume/arrays: " + path);
                format = DxgiFormat(dxgi);
                offset = 148;
            }
            else format = LegacyFormat(bytes, fourCC);
            if (!string.IsNullOrEmpty(viewFormat)) format = ViewFormat(viewFormat);
            return new Header { bytes = bytes, width = width, height = height, mipCount = mips,
                offset = offset, cube = cube, format = format };
        }

        static GraphicsFormat ViewFormat(string value)
        {
            switch (value.ToUpperInvariant())
            {
                case "BC1_UNORM": return GraphicsFormat.RGBA_DXT1_UNorm;
                case "BC5_UNORM": return GraphicsFormat.RG_BC5_UNorm;
                case "BC7_SRGB": return GraphicsFormat.RGBA_BC7_SRGB;
                case "BC7_UNORM": return GraphicsFormat.RGBA_BC7_UNorm;
                case "BC6_UFLOAT": case "BC6H_UFLOAT": return GraphicsFormat.RGB_BC6H_UFloat;
                case "BC6_SFLOAT": case "BC6H_SFLOAT": return GraphicsFormat.RGB_BC6H_SFloat;
                default: return (GraphicsFormat)Enum.Parse(typeof(GraphicsFormat), value, true);
            }
        }

        static GraphicsFormat DxgiFormat(uint value)
        {
            switch (value)
            {
                case 2: return GraphicsFormat.R32G32B32A32_SFloat;
                case 10: return GraphicsFormat.R16G16B16A16_SFloat;
                case 16: return GraphicsFormat.R32G32_SFloat;
                case 27: case 28: return GraphicsFormat.R8G8B8A8_UNorm;
                case 29: return GraphicsFormat.R8G8B8A8_SRGB;
                case 34: return GraphicsFormat.R16G16_SFloat;
                case 41: return GraphicsFormat.R32_SFloat;
                case 49: return GraphicsFormat.R8G8_UNorm;
                case 54: return GraphicsFormat.R16_SFloat;
                case 61: return GraphicsFormat.R8_UNorm;
                case 70: case 71: return GraphicsFormat.RGBA_DXT1_UNorm;
                case 72: return GraphicsFormat.RGBA_DXT1_SRGB;
                case 73: case 74: return GraphicsFormat.RGBA_DXT3_UNorm;
                case 75: return GraphicsFormat.RGBA_DXT3_SRGB;
                case 76: case 77: return GraphicsFormat.RGBA_DXT5_UNorm;
                case 78: return GraphicsFormat.RGBA_DXT5_SRGB;
                case 79: case 80: return GraphicsFormat.R_BC4_UNorm;
                case 81: return GraphicsFormat.R_BC4_SNorm;
                case 82: case 83: return GraphicsFormat.RG_BC5_UNorm;
                case 84: return GraphicsFormat.RG_BC5_SNorm;
                case 87: return GraphicsFormat.B8G8R8A8_UNorm;
                case 91: return GraphicsFormat.B8G8R8A8_SRGB;
                case 94: case 95: return GraphicsFormat.RGB_BC6H_UFloat;
                case 96: return GraphicsFormat.RGB_BC6H_SFloat;
                case 97: case 98: return GraphicsFormat.RGBA_BC7_UNorm;
                case 99: return GraphicsFormat.RGBA_BC7_SRGB;
                default: throw new NotSupportedException("Unsupported DDS DXGI format: " + value);
            }
        }

        static GraphicsFormat LegacyFormat(byte[] bytes, uint fourCC)
        {
            switch (fourCC)
            {
                case 0x31545844: return GraphicsFormat.RGBA_DXT1_UNorm;
                case 0x33545844: return GraphicsFormat.RGBA_DXT3_UNorm;
                case 0x35545844: return GraphicsFormat.RGBA_DXT5_UNorm;
                case 0x31495441: case 0x55344342: return GraphicsFormat.R_BC4_UNorm;
                case 0x32495441: case 0x55354342: return GraphicsFormat.RG_BC5_UNorm;
                case 113: return GraphicsFormat.R16G16B16A16_SFloat;
                case 116: return GraphicsFormat.R32G32B32A32_SFloat;
                case 0:
                    uint bits = BitConverter.ToUInt32(bytes, 88), redMask = BitConverter.ToUInt32(bytes, 92);
                    if (bits == 8) return GraphicsFormat.R8_UNorm;
                    if (bits == 16 && redMask == 0xffff) return GraphicsFormat.R16_UNorm;
                    if (bits == 32) return redMask == 0x00ff0000 ? GraphicsFormat.B8G8R8A8_UNorm : GraphicsFormat.R8G8B8A8_UNorm;
                    break;
            }
            throw new NotSupportedException("Unsupported legacy DDS pixel format: " + fourCC);
        }
    }
}
