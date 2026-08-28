from src.discrepancy import calculate_discrepancy


def polygon(coords):

    return {
        "type": "Polygon",
        "coordinates": [coords],
    }


def test_identical_polygons():

    geometry = polygon([
        [0, 0],
        [10, 0],
        [10, 10],
        [0, 10],
        [0, 0],
    ])

    result = calculate_discrepancy(
        geometry,
        geometry,
    )

    assert result.normalized_discrepancy == 0.0
    assert result.area_difference_ratio == 0.0