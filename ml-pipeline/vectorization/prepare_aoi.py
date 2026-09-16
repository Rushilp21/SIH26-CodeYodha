"""Create a bounded, georeferenced vectorization AOI on Jarvis persistent storage."""

import json
import warnings
from pathlib import Path
from urllib.request import Request, urlopen

import geopandas as gpd
import pyogrio
import rasterio
from rasterio.windows import from_bounds
from shapely.geometry import box
from shapely.ops import polygonize, unary_union

ROOT = Path("/home/jl_fs/bhumisetu")
DEST = ROOT / "datasets/cadastrevision/vectorization_v2"
HOST = "https://phys-techsciences.datastations.nl"
IMAGERY_FILE_ID = 101957
REFERENCE_FILE_ID = 261805
AOI_MARGIN_M = 25.0


def remote(file_id: int) -> str:
    request = Request(f"{HOST}/api/access/datafile/{file_id}", headers={"Range": "bytes=0-4095"})
    with urlopen(request, timeout=45) as response:
        if response.status != 206:
            raise RuntimeError("Range access unavailable; refusing a full dataset download")
        return "/vsicurl/" + response.url


def main() -> None:
    DEST.mkdir(parents=True, exist_ok=True)
    manifest_path = DEST / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        required = [manifest["image"], manifest["reference_lines"], manifest["reference_faces"]]
        if all(Path(path).exists() for path in required):
            print("AOI EXISTS", json.dumps(manifest, indent=2), flush=True)
            return

    options = {
        "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
        "GDAL_HTTP_TIMEOUT": "45",
        "CPL_VSIL_CURL_USE_HEAD": "NO",
    }
    warnings.filterwarnings("ignore", message=".*non conformant file extension.*")
    pyogrio.set_gdal_config_options(options)
    target = gpd.read_file(ROOT / "geojson/parcels_topology_cleaned.geojson")
    if target.crs is None:
        raise RuntimeError("Target GeoJSON has no CRS")

    with rasterio.Env(**options), rasterio.open(remote(IMAGERY_FILE_ID)) as source:
        if source.crs is None or source.transform.is_identity:
            raise RuntimeError("CadastreVision imagery is not georeferenced")
        projected = target.to_crs(source.crs)
        minx, miny, maxx, maxy = projected.total_bounds
        requested = (minx - AOI_MARGIN_M, miny - AOI_MARGIN_M, maxx + AOI_MARGIN_M, maxy + AOI_MARGIN_M)
        window = from_bounds(*requested, transform=source.transform).round_offsets().round_lengths()
        if window.width * window.height > 90_000_000:
            raise RuntimeError("AOI exceeds the bounded 90M-pixel safety limit")
        if window.col_off < 0 or window.row_off < 0 or window.col_off + window.width > source.width or window.row_off + window.height > source.height:
            raise RuntimeError("AOI falls outside the official imagery tile")

        image_path = DEST / "vectorization_aoi.tif"
        profile = source.profile.copy()
        profile.update(
            driver="GTiff",
            width=int(window.width),
            height=int(window.height),
            count=3,
            transform=source.window_transform(window),
            compress="deflate",
            tiled=True,
            blockxsize=512,
            blockysize=512,
            BIGTIFF="IF_SAFER",
        )
        if not image_path.exists():
            with rasterio.open(image_path, "w", **profile) as output:
                for _, block in output.block_windows(1):
                    source_window = rasterio.windows.Window(
                        window.col_off + block.col_off,
                        window.row_off + block.row_off,
                        block.width,
                        block.height,
                    )
                    output.write(source.read([1, 2, 3], window=source_window), window=block)
                    output.write_mask(source.dataset_mask(window=source_window), window=block)
        with rasterio.open(image_path) as check:
            assert check.crs == source.crs and check.transform == profile["transform"]
            assert check.width == int(window.width) and check.height == int(window.height)
            bounds = tuple(check.bounds)

    references = pyogrio.read_dataframe(remote(REFERENCE_FILE_ID), layer="brk_reference", bbox=bounds)
    if references.crs is None:
        raise RuntimeError("CadastreVision reference geometry has no CRS")
    references = references.to_crs(profile["crs"])
    references = references.clip(box(*bounds), keep_geom_type=False)
    references = references[~references.geometry.is_empty & references.geometry.notna()].copy()
    lines_path = DEST / "vectorization_aoi_reference_lines.gpkg"
    references.to_file(lines_path, driver="GPKG")

    interior = box(*bounds).buffer(-5)
    faces = [
        polygon
        for polygon in polygonize(unary_union(references.geometry.tolist()))
        if polygon.is_valid and interior.contains(polygon) and 20 < polygon.area < 250_000
    ]
    if not faces:
        raise RuntimeError("No closed reference cadastral faces exist in the AOI")
    faces_path = DEST / "vectorization_aoi_reference_faces.gpkg"
    gpd.GeoDataFrame({"reference_id": range(len(faces))}, geometry=faces, crs=profile["crs"]).to_file(
        faces_path, driver="GPKG"
    )

    manifest = {
        "name": "vectorization_aoi",
        "source_doi": "10.17026/PT/OS3OWX",
        "license": "CC-BY-4.0",
        "image": str(image_path),
        "crs": str(profile["crs"]),
        "transform": list(profile["transform"])[:6],
        "bounds": bounds,
        "shape": [int(profile["height"]), int(profile["width"])],
        "pixel_count": int(profile["height"] * profile["width"]),
        "reference_lines": str(lines_path),
        "reference_faces": str(faces_path),
        "reference_count": len(faces),
        "aoi_source": "bounds of cleaned target polygons plus 25 metre context",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print("AOI PASS", json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    main()
