"""将 rdc2dcc 角色流程和已映射材质整合为 Unity 导入清单，不在运行时解释截帧。"""
from pathlib import Path
import json
import re

ROOT = Path(__file__).resolve().parents[3]
CONTENT = ROOT / "pro/Authoring/Extracted/SI1"
SOURCE = CONTENT / "Source"


def main():
    scene = json.loads((SOURCE / "scene.rdc2scene").read_text(encoding="utf-8-sig"))
    mapping_path = SOURCE / "semantic-material-bindings.json"
    mapping = json.loads(mapping_path.read_text(encoding="utf-8-sig"))
    mapped = {int(x.get("sourceEvent", x.get("eid", 0))): x for x in mapping.get("materials", mapping.get("parts", []))}
    parts = []
    # 明确的 SI-1 角色几何选择；来源事件只用于离线配对，运行时没有 EID 分支。
    selected = set(mapped)
    names = {488: "FaceDetail", 502: "Eyes", 520: "ClothingSurfaceA", 538: "BodySkinViewTint",
             553: "FaceSkinDetail", 568: "FaceSkin", 585: "ClothingSurfaceB",
             599: "ClothingSurfaceC", 617: "Hair", 655: "EnvironmentSurface", 1190: "EnvironmentEffect"}
    previous_names = {488: "Face", 538: "ClothingViewTintA", 553: "FaceSkin", 568: "BodySkin"}
    for source in scene["parts"]:
        eid = source["eid"]
        if eid not in selected:
            continue
        part = dict(mapped[eid])
        part.update(sourceEvent=eid, binary=f"world2/eid-{eid}.world2", placed=source["placed"],
                    placement=[v for row in source["matrix_scene"] for v in row],
                    materialName=f"SI1_{names.get(eid, 'Surface')}_{eid}",
                    category="Character" if eid < 635 else "Environment",
                    castShadows=eid in {488, 520, 538, 553, 568, 585, 599, 617})
        if eid in previous_names:
            part["previousMaterialName"] = f"SI1_{previous_names[eid]}_{eid}"
        part.setdefault("shader", "Endfield/HybridLit")
        part.setdefault("renderQueue", 2000)
        part.setdefault("keywords", [])
        part.setdefault("scalars", [])
        part.setdefault("vectors", [])
        for binding in part["textures"]:
            if "path" not in binding:
                rid = str(binding["resourceId"]).split("::")[-1]
                binding["path"] = f"Textures/tex_{rid}.png"
        parts.append(part)
    # 独立环境模型和后续特效采用同一发布协议，来源目录不进入运行时。
    background_path = CONTENT / "Background/import.json"
    if background_path.exists():
        background = json.loads(background_path.read_text(encoding="utf-8-sig"))
        parts.append(dict(sourceEvent=background["sourceEvent"], sourceMaterialEvent=background["surfaceEvent"],
                          materialName="SI1_BackgroundPlatform", shader=background["shader"],
                          binary="../" + background["meshPath"], placed=False, renderQueue=2900, category="Environment",
                          keywords=[],
                          textures=[dict(property=k, path=v, srgb=k == "_BaseMap") for k,v in background["textures"].items()],
                          scalars=[dict(property=k,value=v) for k,v in background["floats"].items()],
                          vectors=[dict(property=k,value=v) for k,v in background["vectors"].items()]))
    effect_binding_path = SOURCE / "semantic-effect-bindings.json"
    if effect_binding_path.exists():
        effects = json.loads((CONTENT / "Effects/import.json").read_text(encoding="utf-8-sig"))
        geometry = {draw["eid"]: draw for draw in effects["draws"]}
        bindings = json.loads(effect_binding_path.read_text(encoding="utf-8-sig"))
        layered_path = SOURCE / "semantic-layered-material-bindings.json"
        if layered_path.exists():
            bindings["parts"].extend(json.loads(layered_path.read_text(encoding="utf-8-sig"))["parts"])
        bindings["parts"].sort(key=lambda part: part["sourceEvent"])
        for index, material in enumerate(bindings["parts"]):
            eid = material["sourceEvent"]
            draw = geometry[eid]
            part = dict(material)
            part.update(binary="../" + draw["meshPath"], placed=False, category="Effects",
                        vertexColorPath=draw["vertexColorPath"])
            part.setdefault("castShadows", False)
            part.setdefault("materialName", f"SI1_InkEffect_{index + 1}_{eid}")
            part.setdefault("renderQueue", 3000 + index)
            projection_origin_path = CONTENT / f"Effects/{eid}/projection-origin.json"
            if projection_origin_path.exists():
                projection_data = json.loads(projection_origin_path.read_text(encoding="utf-8-sig"))
                delta = [a-b for a,b in zip(projection_data["sceneFrameRoot"], scene["origin"]["point"])]
                part.setdefault("vectors", []).append(dict(property="_InkProjectionOriginOS", value=[-delta[0], delta[2], delta[1], 0]))
            parts.append(part)
        # 源shadow424与透明1649共享IB/VB，但需要真实随机alpha覆盖模型，不能用不透明占位。
        shadow_only_path = CONTENT / "Effects/shadow-only-import.json"
        if shadow_only_path.exists():
            shadow_bindings = json.loads(shadow_only_path.read_text(encoding="utf-8-sig"))
            for binding in shadow_bindings["parts"]:
                eid = binding["sourceEvent"]
                if any(part["sourceEvent"] == eid for part in parts):
                    continue
                caster = dict(binding)
                caster.update(binary="../" + geometry[eid]["meshPath"], placed=False, category="Effects",
                              shadowsOnly=True, castShadows=True)
                caster.setdefault("renderQueue", 2000)
                caster.setdefault("materialName", f"SI1_EffectShadowCaster_{eid}")
                parts.append(caster)
    # 离线模型方向与实际PostVS逐vertex配对，运行材质只使用Mesh自身方向和Unity动态变换。
    directions_path = CONTENT / "CharacterDirections/import.json"
    if directions_path.exists():
        directions = {entry["sourceEvent"]: entry for entry in json.loads(directions_path.read_text(encoding="utf-8-sig"))["parts"]}
        for part in parts:
            if part["sourceEvent"] in directions:
                part["normalTangentPath"] = directions[part["sourceEvent"]]["normalTangentPath"]
    camera = scene["camera"]
    # 颜色数据以GPU实际解码值发布；原SRV的sRGB标记只作来源说明，不能再次应用。
    native_index_path = CONTENT / "TexturesNative/index.json"
    if native_index_path.exists():
        native_by_binding = {}
        native_by_resource = {}
        for texture in json.loads(native_index_path.read_text(encoding="utf-8-sig"))["textures"]:
            relative = "TexturesNative/" + texture["importPath"]
            native = json.loads((CONTENT / relative).read_text(encoding="utf-8-sig"))
            native_by_resource[int(texture["resourceId"])] = relative
            for consumer in native["consumers"]:
                native_by_binding[(consumer["sourceEvent"], consumer["property"])] = relative
        for part in parts:
            for binding in part.get("textures", []):
                native_path = native_by_binding.get((part.get("sourceMaterialEvent", part["sourceEvent"]), binding["property"]))
                if not native_path:
                    resource_match = re.search(r"(?:tex_|ResourceId_)(\d+)", binding["path"])
                    if resource_match:
                        native_path = native_by_resource.get(int(resource_match.group(1)))
                if native_path:
                    binding["nativeImportPath"] = native_path
    result = dict(origin=scene["origin"]["point"], cameraPosition=camera["position"],
                  cameraRotation=[v for row in camera["matrix"] for v in row],
                  fieldOfView=camera["half_fov_y_deg"]*2, aspect=camera["aspect"], parts=parts)
    lighting = json.loads((SOURCE / "semantic-scene-settings.json").read_text(encoding="utf-8-sig"))
    result["mainLightDirection"] = lighting["directionTowardLight"]
    result["mainLightRadiance"] = lighting["linearRadiance"]
    result["ambientRadiance"] = lighting["linearAmbientRadiance"]
    result["characterShadowProfile"] = lighting["characterShadowProfile"]
    if (CONTENT / "EnvironmentReflection/11550/import.json").exists():
        result["environmentReflection"] = "EnvironmentReflection/11550/import.json"
    (SOURCE / "scene-import.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Prepared {len(parts)} parts -> {SOURCE / 'scene-import.json'}")


if __name__ == "__main__":
    main()
