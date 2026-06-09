#!/usr/bin/env python3
"""
FM2 Phase 1: 全 bundle スキャン + wanzer 候補特定
- 2,313個の.bundleを1つずつ開いて中身を調査
- Meshを持つbundleを記録
- ファイル名 / オブジェクト名からwanzer関連を特定
- メモリ監視 + gc で安全に処理
- 結果: JSON + テキストレポート
"""

import os, sys, json, gc, time
from pathlib import Path

# ── config ──
BUNDLE_DIR = "/mnt/disk_e/FRONT MISSION 2 Remake/Front Mission 2 Remake_Data/StreamingAssets/aa/StandaloneWindows64"
OUT_DIR = Path.home() / "FM2_extracted" / "scans"
OUT_DIR.mkdir(parents=True, exist_ok=True)

WANZER_KEYWORDS = [
    "wanzer", "mech", "robot", "body", "arm", "leg", "head",
    "weapon", "gun", "cannon", "rifle", "missile", "launcher",
    "sword", "shield", "backpack", "thruster", "engine",
    "zenith", "frost", "vapor", "assault", "buster", "striker",
    "networkprefabs", "prefab", "vehicle", "unit", "parts"
]

# ── helpers ──
def is_wanzer_related(filename, obj_names):
    """ファイル名 or オブジェクト名にwanzer関連キーワードが含まれるか"""
    low = filename.lower()
    if any(k in low for k in WANZER_KEYWORDS):
        return True
    if obj_names:
        low_names = " ".join(n.lower() for n in obj_names)
        if any(k in low_names for k in WANZER_KEYWORDS):
            return True
    return False


def scan_bundle(path):
    """1 bundle の中身を調査。UnityPyで開いて型・Mesh名を取得。"""
    import UnityPy
    env = UnityPy.load(str(path))
    types = {}
    mesh_names = []
    obj_names = []
    has_texture = False
    has_material = False
    has_gameobject = False

    for obj in env.objects:
        t = obj.type.name
        types[t] = types.get(t, 0) + 1
        if t == "Mesh":
            try:
                m = obj.read()
                name = getattr(m, "m_Name", getattr(m, "name", "unknown"))
                mesh_names.append(name)
                obj_names.append(name)
            except Exception as e:
                mesh_names.append(f"<read_error:{e}")
        elif t == "GameObject":
            has_gameobject = True
            try:
                go = obj.read()
                n = getattr(go, "m_Name", getattr(go, "name", ""))
                if n:
                    obj_names.append(n)
            except:
                pass
        elif t == "Texture2D":
            has_texture = True
        elif t == "Material":
            has_material = True

    # env を明示的に解放（大きいbundle対策）
    del env
    gc.collect()

    return {
        "path": str(path),
        "size": os.path.getsize(path),
        "types": types,
        "mesh_count": len(mesh_names),
        "mesh_names": mesh_names,
        "obj_names": obj_names,
        "has_texture": has_texture,
        "has_material": has_material,
        "has_gameobject": has_gameobject,
    }


def main():
    bundles = sorted(
        [Path(BUNDLE_DIR) / f for f in os.listdir(BUNDLE_DIR) if f.endswith(".bundle")],
        key=lambda p: p.stat().st_size  # 小さいものから順番に処理
    )
    total = len(bundles)
    print(f"🔍 Phase 1: scanning {total} bundles...")
    print(f"   → output: {OUT_DIR}")
    print(f"   → sorted by size (smallest first)")
    print()

    results = []
    wanzer_candidates = []
    errors = []
    start = time.time()

    try:
        from tqdm import tqdm
        iterator = tqdm(enumerate(bundles), total=total, ncols=80)
    except ImportError:
        iterator = enumerate(bundles)

    for i, bp in iterator:
        try:
            info = scan_bundle(bp)
            results.append(info)

            if info["mesh_count"] > 0 and is_wanzer_related(bp.name, info["obj_names"]):
                wanzer_candidates.append(info)
                if not hasattr(iterator, "set_postfix"):  # tqdm以外
                    print(f"  🎯 {bp.name}: {info['mesh_count']} meshes")
            elif info["mesh_count"] > 0 and not hasattr(iterator, "set_postfix"):
                # meshありだがwanzer候補外（一旦記録）
                pass

            # 100個ごとに中間保存（クラッシュ対策）
            if (i + 1) % 100 == 0:
                _save_checkpoint(results, wanzer_candidates, OUT_DIR, i + 1)

        except Exception as e:
            errors.append({"path": str(bp), "error": str(e)})
            print(f"  ❌ ERROR {bp.name}: {e}")
            gc.collect()

    elapsed = time.time() - start

    # ── 最終保存 ──
    _save_checkpoint(results, wanzer_candidates, OUT_DIR, total, final=True)

    # ── サマリー ──
    mesh_bundles = [r for r in results if r["mesh_count"] > 0]
    summary = {
        "total_bundles": total,
        "mesh_bundles": len(mesh_bundles),
        "wanzer_candidates": len(wanzer_candidates),
        "total_meshes": sum(r["mesh_count"] for r in mesh_bundles),
        "errors": len(errors),
        "elapsed_sec": round(elapsed, 2),
    }
    (OUT_DIR / "phase1_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False)
    )
    (OUT_DIR / "phase1_errors.json").write_text(
        json.dumps(errors, indent=2, ensure_ascii=False)
    )

    print()
    print("=" * 50)
    print("✅ Phase 1 COMPLETE")
    print(f"   scanned:      {total}")
    print(f"   mesh bundles: {len(mesh_bundles)}")
    print(f"   wanzer hits:  {len(wanzer_candidates)}")
    print(f"   total meshes: {sum(r['mesh_count'] for r in mesh_bundles)}")
    print(f"   errors:       {len(errors)}")
    print(f"   time:         {elapsed:.1f}s")
    print(f"   output:       {OUT_DIR}")
    print("=" * 50)


def _save_checkpoint(results, wanzer_candidates, out_dir, count, final=False):
    label = "final" if final else f"chk_{count}"
    (out_dir / f"phase1_results_{label}.json").write_text(
        json.dumps(results, indent=2, ensure_ascii=False)
    )
    (out_dir / f"phase1_wanzers_{label}.json").write_text(
        json.dumps(wanzer_candidates, indent=2, ensure_ascii=False)
    )


if __name__ == "__main__":
    main()
