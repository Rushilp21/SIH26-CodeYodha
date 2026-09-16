"""Prepare diverse, disjoint CadastreVision windows using HTTP range reads only."""

from __future__ import annotations

import argparse
import json
import time
import warnings
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import geopandas as gpd
import numpy as np
import pyogrio
import rasterio
from rasterio.windows import Window
from pyproj import Transformer
from shapely.geometry import LineString, Polygon, box
from shapely.ops import polygonize, unary_union

ROOT = Path("/home/jl_fs/bhumisetu")
HOST = "https://phys-techsciences.datastations.nl"
IMAGERY_FILE_ID = 101957
REFERENCE_FILE_ID = 261805
WINDOW_SIZE = 1536
MIN_REFERENCE_LENGTH_M = 200.0
MIN_REFERENCE_FACES = 2
OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="finetune_v3")
    parser.add_argument("--train-count", type=int, default=9)
    parser.add_argument("--validation-count", type=int, default=3)
    parser.add_argument("--test-count", type=int, default=3)
    return parser.parse_args()


def remote(file_id: int) -> str:
    request = Request(f"{HOST}/api/access/datafile/{file_id}", headers={"Range": "bytes=0-4095"})
    with urlopen(request, timeout=45) as response:
        if response.status != 206:
            raise RuntimeError("Range access unavailable; refusing a full dataset download")
        return "/vsicurl/" + response.url


def write_image_window(source, window: Window, destination: Path) -> tuple:
    profile = source.profile.copy()
    profile.update(
        driver="GTiff", width=int(window.width), height=int(window.height), count=3,
        transform=source.window_transform(window), tiled=True, blockxsize=512,
        blockysize=512, compress="deflate", BIGTIFF="IF_SAFER",
    )
    temporary = destination.with_name(f".{destination.name}.tmp")
    with rasterio.open(temporary, "w", **profile) as output:
        for _, block in output.block_windows(1):
            source_window = Window(
                window.col_off + block.col_off, window.row_off + block.row_off,
                block.width, block.height,
            )
            output.write(source.read([1, 2, 3], window=source_window), window=block)
            output.write_mask(source.dataset_mask(window=source_window), window=block)
    temporary.replace(destination)
    return tuple(rasterio.windows.bounds(window, source.transform))


def hard_negative_features(bounds: tuple, source_crs) -> gpd.GeoDataFrame:
    """Fetch real OSM roads, buildings, and waterways for one selected crop."""
    west, south, east, north = gpd.GeoSeries([box(*bounds)], crs=source_crs).to_crs("EPSG:4326").total_bounds
    query = f"""[out:json][timeout:90];(
      way[\"highway\"]({south},{west},{north},{east});
      way[\"building\"]({south},{west},{north},{east});
      way[\"waterway\"]({south},{west},{north},{east});
    );out tags geom;"""
    payload = urlencode({"data": query}).encode()
    response = None
    last_error = None
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            request = Request(endpoint, data=payload, headers={"User-Agent": "BhumiSetu-training-preparation/1.0"})
            with urlopen(request, timeout=120) as handle:
                response = json.loads(handle.read())
            break
        except Exception as error:
            last_error = error
            time.sleep(2)
    if response is None:
        # The standard OSM map endpoint is appropriate here because every crop
        # is only 384 x 384 metres. It is a bounded fallback, not a bulk extract.
        map_url = f"https://api.openstreetmap.org/api/0.6/map?bbox={west},{south},{east},{north}"
        try:
            request = Request(map_url, headers={"User-Agent": "BhumiSetu-training-preparation/1.0"})
            with urlopen(request, timeout=120) as handle:
                root = ET.fromstring(handle.read())
            nodes = {node.attrib["id"]: (float(node.attrib["lon"]), float(node.attrib["lat"]))
                     for node in root.findall("node")}
            elements = []
            for way in root.findall("way"):
                tags = {tag.attrib["k"]: tag.attrib["v"] for tag in way.findall("tag")}
                geometry = [
                    {"lon": nodes[item.attrib["ref"]][0], "lat": nodes[item.attrib["ref"]][1]}
                    for item in way.findall("nd") if item.attrib["ref"] in nodes
                ]
                elements.append({"id": int(way.attrib["id"]), "tags": tags, "geometry": geometry})
            response = {"elements": elements}
        except Exception as error:
            raise RuntimeError(f"OSM hard-negative queries failed: overpass={last_error}; map={error}") from error

    rows = []
    for element in response.get("elements", []):
        coordinates = [(point["lon"], point["lat"]) for point in element.get("geometry", [])]
        tags = element.get("tags", {})
        if len(coordinates) < 2:
            continue
        if "building" in tags and len(coordinates) >= 4 and coordinates[0] == coordinates[-1]:
            geometry, feature_type = Polygon(coordinates), "building"
        elif "highway" in tags:
            geometry, feature_type = LineString(coordinates), "road"
        elif "waterway" in tags:
            geometry, feature_type = LineString(coordinates), "canal"
        else:
            continue
        if geometry.is_valid and not geometry.is_empty:
            rows.append({"osm_id": int(element["id"]), "feature_type": feature_type, "geometry": geometry})
    if not rows:
        raise RuntimeError("Selected window contains no OSM road/building/canal hard-negative evidence")
    frame = gpd.GeoDataFrame(rows, crs="EPSG:4326").to_crs(source_crs)
    frame = frame.clip(box(*bounds), keep_geom_type=False)
    frame = frame[frame.geometry.notna() & ~frame.geometry.is_empty & frame.geometry.is_valid].copy()
    if frame.empty:
        raise RuntimeError("OSM hard-negative evidence does not intersect the selected window")
    return frame


def main() -> None:
    args = arguments()
    requested_count = args.train_count + args.validation_count + args.test_count
    if min(args.train_count, args.validation_count, args.test_count) < 1:
        raise ValueError("Train, validation, and test counts must all be positive")
    destination = ROOT / "datasets/cadastrevision" / args.version
    manifest_path = destination / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        required = [
            item[path] for item in manifest["records"]
            for path in ("image", "reference_lines", "reference_faces", "hard_negative_features")
        ]
        if all(Path(path).is_file() for path in required):
            print("DATASET EXISTS", json.dumps(manifest, indent=2), flush=True)
            return
        raise RuntimeError(f"Incomplete dataset exists at {destination}; inspect before retrying")
    destination.mkdir(parents=True, exist_ok=False)

    options = {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR", "GDAL_HTTP_TIMEOUT": "45", "CPL_VSIL_CURL_USE_HEAD": "NO"}
    warnings.filterwarnings("ignore", message=".*non conformant file extension.*")
    pyogrio.set_gdal_config_options(options)
    imagery_remote, reference_remote = remote(IMAGERY_FILE_ID), remote(REFERENCE_FILE_ID)
    candidates = []
    with rasterio.Env(**options), rasterio.open(imagery_remote) as source:
        if source.crs is None or source.transform.is_identity:
            raise RuntimeError("CadastreVision imagery is not georeferenced")
        # A bounded deterministic 6x6 lattice expands geographic coverage while
        # keeping HTTP range reads and persistent storage small.
        grid_size = 6
        row_offsets = [int(value) for value in np.linspace(0, source.height - WINDOW_SIZE, grid_size)]
        col_offsets = [int(value) for value in np.linspace(0, source.width - WINDOW_SIZE, grid_size)]
        target_manifest = json.loads((ROOT / "datasets/cadastrevision/vectorization_v2/manifest.json").read_text())
        target_box = box(*target_manifest["bounds"])
        probed = 0
        for row in row_offsets:
            for col in col_offsets:
                probed += 1
                window = Window(col, row, WINDOW_SIZE, WINDOW_SIZE)
                bounds = tuple(rasterio.windows.bounds(window, source.transform))
                if box(*bounds).intersects(target_box):
                    continue
                lines = pyogrio.read_dataframe(reference_remote, layer="brk_reference", bbox=bounds)
                if lines.crs is None or lines.empty:
                    continue
                lines = lines.to_crs(source.crs).clip(box(*bounds), keep_geom_type=False)
                lines = lines[lines.geometry.notna() & ~lines.geometry.is_empty & lines.geometry.is_valid].copy()
                faces = [
                    face for face in polygonize(unary_union(lines.geometry.tolist()))
                    if face.is_valid and box(*bounds).buffer(-5).contains(face) and 20 < face.area < 250_000
                ]
                line_length = float(lines.length.sum())
                if len(faces) >= MIN_REFERENCE_FACES and line_length >= MIN_REFERENCE_LENGTH_M:
                    candidates.append({"row": row, "col": col, "bounds": bounds, "lines": lines, "faces": faces,
                                       "reference_count": len(faces), "line_length_m": line_length})
                print(f"PROBE {probed}/{grid_size ** 2} suitable={len(candidates)}", flush=True)
        if len(candidates) < requested_count:
            raise RuntimeError(f"Only {len(candidates)} suitable disjoint windows found; need {requested_count}")

        # Stratified deterministic selection spans low, medium, and high line densities.
        candidates.sort(key=lambda item: item["line_length_m"])
        indices = [round(index * (len(candidates) - 1) / (requested_count - 1)) for index in range(requested_count)]
        selected = [candidates[index] for index in dict.fromkeys(indices)]
        if len(selected) != requested_count:
            raise RuntimeError("Density stratification produced duplicate windows")
        remaining = {"train": args.train_count, "validation": args.validation_count, "test": args.test_count}
        split_order, cycle = [], ("train", "validation", "train", "test")
        while len(split_order) < requested_count:
            progressed = False
            for split in cycle:
                if remaining[split] > 0:
                    split_order.append(split)
                    remaining[split] -= 1
                    progressed = True
            if not progressed:
                break
        counters = {"train": 0, "validation": 0, "test": 0}
        split_names = []
        for split in split_order:
            prefix = "train_selected" if split == "train" else split
            split_names.append(f"{prefix}_{counters[split]}")
            counters[split] += 1
        records = []
        for name, selected_window in zip(split_names, selected):
            window = Window(selected_window["col"], selected_window["row"], WINDOW_SIZE, WINDOW_SIZE)
            image_path = destination / f"{name}.tif"
            bounds = write_image_window(source, window, image_path)
            lines_path = destination / f"{name}_reference_lines.gpkg"
            faces_path = destination / f"{name}_reference_faces.gpkg"
            negatives_path = destination / f"{name}_hard_negatives.gpkg"
            selected_window["lines"].to_file(lines_path, driver="GPKG")
            gpd.GeoDataFrame(
                {"reference_id": range(len(selected_window["faces"]))},
                geometry=selected_window["faces"], crs=source.crs,
            ).to_file(faces_path, driver="GPKG")
            negatives = hard_negative_features(bounds, source.crs)
            negatives.to_file(negatives_path, driver="GPKG")
            negative_counts = {key: int(value) for key, value in negatives["feature_type"].value_counts().items()}
            split = "train" if name.startswith("train_") else ("validation" if name.startswith("validation") else "test")
            records.append({
                "name": name, "split": split, "image": str(image_path),
                "reference": str(faces_path), "reference_lines": str(lines_path),
                "reference_faces": str(faces_path), "crs": source.crs.to_string(),
                "hard_negative_features": str(negatives_path), "hard_negative_counts": negative_counts,
                "transform": list(source.window_transform(window))[:6], "bounds": bounds,
                "shape": [WINDOW_SIZE, WINDOW_SIZE], "reference_count": selected_window["reference_count"],
                "reference_line_length_m": selected_window["line_length_m"],
            })

    manifest = {
        "version": args.version, "source_doi": "10.17026/PT/OS3OWX", "license": "CC-BY-4.0",
        "selection": "deterministic density-stratified disjoint 1536px windows; target AOI excluded",
        "hard_negative_source": "OpenStreetMap contributors via Overpass; roads, buildings, and waterways",
        "hard_negative_license": "ODbL-1.0",
        "target_aoi_used_for_training_or_selection": False, "records": records,
    }
    temporary_manifest = manifest_path.with_suffix(".tmp.json")
    temporary_manifest.write_text(json.dumps(manifest, indent=2))
    temporary_manifest.replace(manifest_path)
    print("DATASET PASS", json.dumps(manifest, indent=2), flush=True)


if __name__ == "__main__":
    main()
