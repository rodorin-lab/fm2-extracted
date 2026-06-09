#!/usr/bin/env python3
"""
FM2 Phase 2: wanzer 候補 bundle から Mesh を .obj / .fbx 抽出
- Phase1 の JSON を読み込む
- wanzer_candidates.json に含まれる bundle だけを再処理
- Mesh を .obj として出力（fbx/glb は UnityPy のサポート状況次第）
- ファイル名から機体名を推測して整理
- メモリ監視 + 並列ではなく逐次処理（RAM安全）
"""

import os, sys, json, gc, re
from pathlib import Path
import UnityPy

# ── config ──
EXTRACT_DIR = Path.home() / "FM2_extracted" / "wanzers"
EXTRACT_DIR.mkdir(parents=True, exist_ok=True)

# 機体名を抽出する正規表現群
WANZER_NAME_PATTERNS = [
    r"(?i)(networkprefabs_assets_fm_([a-z0-9]+))",
    r"(?i)([a-z]+_[a-z]+_[0-9]+)",
    r"(?i)(wanzer[_-]?[a-z0-9]+)",
    r"(?i)(mech[_-]?[a-z0-9]+)",
]


def sanitize(name):
    """ファイル名に使えない文字を置換"""
    if not name:
        return "unknown"
    return "".join(c if c.isalnum() or c in "_-" else "_" for c in name)[:60]


def guess_wanzer_name(bundle_name, mesh_name):
    """bundle名とmesh名から機体名を推測"""
    base = bundle_name.replace(".bundle", "")
    # 優先: mesh名に 'wanzer' や機体名が含まれてるか
    m = re.search(r"(?i)([a-z][a-z0-9]*[_-]?[a-z0-9]+)", mesh_name)
    if m:
        candidate = m.group(1)
        if len(candidate) > 3:
            return candidate
    return base[:30]


def extract_mesh_to_obj(mesh_obj, out_path):
    """UnityPy Mesh を .obj テキストとして出力"""
    m = mesh_obj.read()
    verts = getattr(m, "m_Vertices", getattr(m, "vertices", []))
    indices = getattr(m, "m_IndexBuffer", getattr(m, "indexBuffer", []))
    uvs = getattr(m, "m_UV", getattr(m, "uv", []))
    normals = getattr(m, "m_Normals", getattr(m, "normals", []))

    lines = ["# FM2 Extracted Mesh", f"# {getattr(m, 'm_Name', 'unknown')}", ""]

    # vertices
    if hasattr(verts, "Count"):
        vert_count = verts.Count // 3
    else:
        vert_count = len(verts) // 3 if len(verts) > 0 else 0

    for i in range(vert_count):
        x = verts[i * 3 + 0] if len(verts) > i * 3 + 0 else 0
        y = verts[i * 3 + 1] if len(verts) > i * 3 + 1 else 0
        z = verts[i * 3 + 2] if len(verts) > i * 3 + 2 else 0
        lines.append(f"v {x} {y} {z}")

    # UVs
    if uvs:
        uv_count = len(uvs) // 2
        for i in range(uv_count):
            u = uvs[i * 2 + 0] if len(uvs) > i * 2 + 0 else 0
            v = uvs[i * 2 + 1] if len(uvs) > i * 2 + 1 else 0
            lines.append(f"vt {u} {v}")

    # normals
    if normals:
        n_count = len(normals) // 3
        for i in range(n_count):
            x = normals[i * 3 + 0] if len(normals) > i * 3 + 0 else 0
            y = normals[i * 3 + 1] if len(normals) > i * 3 + 1 else 0
            z = normals[i * 3 + 2] if len(normals) > i * 3 + 2 else 0
            lines.append(f"vn {x} {y} {z}")

    # faces (triangles)
    if hasattr(indices, "Count"):
        tri_count = indices.Count // 3
    else:
        tri_count = len(indices) // 3

    for i in range(tri_count):
        a = indices[i * 3 + 0] + 1 if len(indices) > i * 3 + 0 else 1
        b = indices[i * 3 + 1] + 1 if len(indices) > i * 3 + 1 else 1
        c = indices[i * 3 + 2] + 1 if len(indices) > i * 3 + 2 else 1
        lines.append(f"f {a} {b} {c}")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return len(lines)


def export_bundle_wanzers(bundle_path, out_dir):
    """1 bundle 内の全 Mesh を .obj として出力。機体ごとにフォルダ分け"""
    env = UnityPy.load(str(bundle_path))
    exports = []
    for obj in env.objects:
        if obj.type.name != "Mesh":
            continue
        try:
            m = obj.read()
            name = getattr(m, "m_Name", getattr(m, "name", "unknown"))
            safe_name = sanitize(name)

            # 機体名推測 → フォルダ作成
            wanzer_name = guess_wanzer_name(Path(bundle_path).name, name)
            wanzer_dir = out_dir / sanitize(wanzer_name)
            wanzer_dir.mkdir(exist_ok=True)

            out_path = wanzer_dir / f"{safe_name}.obj"
            line_count = extract_mesh_to_obj(obj, out_path)
            exports.append({
                "wanzer": wanzer_name,
                "mesh": safe_name,
                "path": str(out_path),
                "lines": line_count,
            })
        except Exception as e:
            exports.append({"error": str(e), "bundle": str(bundle_path)})

    del env
    gc.collect()
    return exports


def main():
    scan_dir = Path.home() / "FM2_extracted" / "scans"
    wanzer_json = scan_dir / "phase1_wanzers_final.json"

    if not wanzer_json.exists():
        print(f"❌ {wanzer_json} not found. Run phase1 first!")
        sys.exit(1)

    candidates = json.loads(wanzer_json.read_text())
    total = len(candidates)
    print(f"🔥 Phase 2: extracting meshes from {total} wanzer bundles...")
    print(f"   → output: {EXTRACT_DIR}")

    all_exports = []
    errors = []

    try:
        from tqdm import tqdm
        iterator = tqdm(candidates, total=total, ncols=80)
    except ImportError:
        iterator = candidates

    for info in iterator:
        path = info["path"]
        try:
            exports = export_bundle_wanzers(path, EXTRACT_DIR)
            all_exports.extend(exports)
            if exports and any("error" not in e for e in exports):
                if hasattr(iterator, "set_postfix"):
                    iterator.set_postfix(last=Path(path).name[:20])
        except Exception as e:
            errors.append({"path": path, "error": str(e)})
            print(f"  ❌ {Path(path).name}: {e}")
            gc.collect()

    # ── 結果保存 ──
    (EXTRACT_DIR.parent / "phase2_exports.json").write_text(
        json.dumps(all_exports, indent=2, ensure_ascii=False)
    )
    summary = {
        "total_candidates": total,
        "exported_meshes": len([e for e in all_exports if "error" not in e]),
        "errors": len(errors),
        "output_dir": str(EXTRACT_DIR),
        "wanzer_dirs": sorted([d.name for d in EXTRACT_DIR.iterdir() if d.is_dir()]),
    }
    (EXTRACT_DIR.parent / "phase2_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False)
    )

    print()
    print("=" * 50)
    print("✅ Phase 2 COMPLETE")
    print(f"   exported meshes: {summary['exported_meshes']}")
    print(f"   wanzer folders:  {len(summary['wanzer_dirs'])}")
    print(f"   errors:          {len(errors)}")
    print(f"   output:          {EXTRACT_DIR}")
    print("=" * 50)


if __name__ == "__main__":
    main()
