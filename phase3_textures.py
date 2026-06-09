#!/usr/bin/env python3
"""
FM2 Phase 3: テクスチャ・マテリアル抽出
- Phase1 の全結果から Texture2D / Material を持つ bundle を列挙
- PNG/JPEG としてテクスチャを出力
- wanzerフォルダに対応するテクスチャをマッチング
"""

import os, sys, json, gc
from pathlib import Path
from PIL import Image
import UnityPy

EXTRACT_DIR = Path.home() / "FM2_extracted"
TEXTURE_DIR = EXTRACT_DIR / "textures"
TEXTURE_DIR.mkdir(parents=True, exist_ok=True)


def save_texture(tex_obj, out_dir, prefix=""):
    """Texture2D を PNG として保存"""
    try:
        tex = tex_obj.read()
        name = getattr(tex, "m_Name", getattr(tex, "name", "unknown"))
        safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in name)[:50]

        # UnityPy 1.x のテクスチャ画像取得方法（バージョン依存）
        img = None
        if hasattr(tex, "image"):
            img = tex.image
        elif hasattr(tex, "m_Image"):
            img = tex.m_Image
        elif hasattr(tex_obj, "read"):
            # fallback: 生バイトから PIL Image 作成
            raw = tex_obj.read_raw()
            if raw:
                try:
                    img = Image.open(raw)
                except:
                    pass

        if img is None:
            return {"name": safe, "status": "no_image_data"}

        out_path = out_dir / f"{prefix}{safe}.png"
        if hasattr(img, "save"):
            img.save(out_path)
        else:
            return {"name": safe, "status": "cannot_save"}

        return {"name": safe, "path": str(out_path), "status": "ok"}
    except Exception as e:
        return {"name": "unknown", "status": f"error:{e}"}


def extract_textures_from_bundle(bundle_path, out_dir):
    """1 bundle 内の全 Texture2D を抽出"""
    env = UnityPy.load(str(bundle_path))
    results = []
    for obj in env.objects:
        if obj.type.name == "Texture2D":
            r = save_texture(obj, out_dir, prefix=f"{Path(bundle_path).stem}_")
            results.append(r)
    del env
    gc.collect()
    return results


def main():
    scan_dir = EXTRACT_DIR / "scans"
    results_json = scan_dir / "phase1_results_final.json"

    if not results_json.exists():
        print(f"❌ {results_json} not found. Run phase1 first!")
        sys.exit(1)

    results = json.loads(results_json.read_text())
    texture_bundles = [r for r in results if r.get("has_texture")]
    total = len(texture_bundles)
    print(f"🖼️ Phase 3: extracting textures from {total} bundles...")

    all_textures = []
    try:
        from tqdm import tqdm
        iterator = tqdm(texture_bundles, total=total, ncols=80)
    except ImportError:
        iterator = texture_bundles

    for info in iterator:
        path = info["path"]
        try:
            texs = extract_textures_from_bundle(path, TEXTURE_DIR)
            all_textures.extend(texs)
        except Exception as e:
            all_textures.append({"error": str(e), "path": path})
            gc.collect()

    # 保存
    summary = {
        "total_texture_bundles": total,
        "extracted_textures": len([t for t in all_textures if t.get("status") == "ok"]),
        "errors": len([t for t in all_textures if "error" in t]),
        "output_dir": str(TEXTURE_DIR),
    }
    (EXTRACT_DIR / "phase3_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False)
    )

    print()
    print("=" * 50)
    print("✅ Phase 3 COMPLETE")
    print(f"   texture bundles: {total}")
    print(f"   extracted:     {summary['extracted_textures']}")
    print(f"   output:        {TEXTURE_DIR}")
    print("=" * 50)


if __name__ == "__main__":
    main()
