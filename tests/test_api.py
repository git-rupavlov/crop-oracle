from fastapi.testclient import TestClient


def create_field(client: TestClient, name: str = "Vartopo observation plot") -> dict:
    response = client.post(
        "/fields",
        json={
            "name": name,
            "workspace_id": 1,
            "location_label": "Park Vartopo, Sofia",
            "area_square_meters": 250,
            "notes": "Approximate public observation area.",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_health(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_list_fields(client: TestClient) -> None:
    field = create_field(client)

    response = client.get("/fields")

    assert response.status_code == 200
    fields = response.json()
    assert len(fields) == 1
    assert fields[0]["id"] == field["id"]
    assert fields[0]["name"] == "Vartopo observation plot"


def test_create_and_list_weed_observations(client: TestClient) -> None:
    field = create_field(client)

    response = client.post(
        f"/fields/{field['id']}/weed-observations",
        json={
            "observed_at": "2026-05-04",
            "species": "Chenopodium album",
            "confidence": 0.8,
            "coverage_percent": 35,
            "density_class": "medium",
            "growth_stage": "seedling",
            "latitude": 42.6581,
            "longitude": 23.2852,
        },
    )

    assert response.status_code == 201
    observation = response.json()
    assert observation["field_id"] == field["id"]
    assert observation["workspace_id"] == 1

    list_response = client.get(f"/fields/{field['id']}/weed-observations")
    assert list_response.status_code == 200
    observations = list_response.json()
    assert len(observations) == 1
    assert observations[0]["species"] == "Chenopodium album"


def test_prediction_shape_and_rule_behavior(client: TestClient) -> None:
    field = create_field(client)
    client.post(
        f"/fields/{field['id']}/weed-observations",
        json={
            "observed_at": "2025-06-03",
            "species": "Chenopodium album",
            "confidence": 0.9,
            "coverage_percent": 45,
            "density_class": "high",
        },
    )

    response = client.post(
        f"/fields/{field['id']}/predict",
        json={
            "target_year": 2026,
            "recent_rainfall_mm": 25,
            "recent_mean_temp_c": 20,
            "disturbed_soil": True,
        },
    )

    assert response.status_code == 200
    prediction_run = response.json()
    assert prediction_run["model_name"] == "rule_based"
    assert prediction_run["predictions"]
    prediction = prediction_run["predictions"][0]
    assert prediction["species"] == "Chenopodium album"
    assert prediction["probability"] >= 0.8
    assert prediction["expected_density_class"] == "high"
    assert prediction["coexistence_recommendation"] == "suppress"

    latest_response = client.get(f"/fields/{field['id']}/predictions/latest")
    assert latest_response.status_code == 200
    assert latest_response.json()["id"] == prediction_run["id"]


def test_validation_errors(client: TestClient) -> None:
    response = client.post(
        "/fields",
        json={
            "name": "",
            "approximate_latitude": 120,
        },
    )

    assert response.status_code == 422


def test_default_workspace_and_geojson(client: TestClient) -> None:
    workspaces_response = client.get("/map/workspaces")
    assert workspaces_response.status_code == 200
    workspaces = workspaces_response.json()
    assert workspaces[0]["name"] == "Park Vartopo"

    field = create_field(client)
    client.post(
        f"/fields/{field['id']}/weed-observations",
        json={
            "observed_at": "2026-05-04",
            "species": "Trifolium repens",
            "confidence": 0.7,
            "coverage_percent": 8,
            "density_class": "low",
            "latitude": 42.6581,
            "longitude": 23.2852,
        },
    )

    geojson_response = client.get("/map/workspaces/1/observations.geojson")
    assert geojson_response.status_code == 200
    feature_collection = geojson_response.json()
    assert feature_collection["type"] == "FeatureCollection"
    assert feature_collection["features"][0]["type"] == "Feature"
    assert feature_collection["features"][0]["geometry"]["type"] == "Point"
    assert feature_collection["features"][0]["properties"]["species"] == "Trifolium repens"


def test_seeded_layers_and_layer_geojson(client: TestClient) -> None:
    response = client.get("/map/workspaces/1/layers")

    assert response.status_code == 200
    layers = response.json()
    layer_names = {layer["name"] for layer in layers}
    assert {
        "Observations",
        "Predicted weeds",
        "Terrain",
        "Moisture",
        "Disturbance",
        "Experiment plots",
        "Walking paths",
    }.issubset(layer_names)

    observations_layer = next(layer for layer in layers if layer["layer_type"] == "observations")
    geojson_response = client.get(f"/map/workspaces/1/layers/{observations_layer['id']}/geojson")
    assert geojson_response.status_code == 200
    assert geojson_response.json()["type"] == "FeatureCollection"


def test_workspace_observation_with_photos_in_geojson(client: TestClient) -> None:
    response = client.post(
        "/map/workspaces/1/observations",
        json={
            "observed_at": "2026-06-15",
            "species": "Urtica dioica",
            "confidence": 0.95,
            "coverage_percent": 80,
            "density_class": "high",
            "geometry_geojson": (
                '{"type":"Polygon","coordinates":[[[23.284,42.658],'
                "[23.285,42.658],[23.285,42.659],[23.284,42.659],[23.284,42.658]]]}"
            ),
            "notes": "Large nettle patch",
            "photos": [
                {
                    "url": "https://example.com/nettle.jpg",
                    "thumbnail_url": "https://example.com/nettle-thumb.jpg",
                    "taken_at": "2026-06-15T09:30:00",
                }
            ],
        },
    )

    assert response.status_code == 201
    observation = response.json()
    assert observation["photos"][0]["url"] == "https://example.com/nettle.jpg"

    geojson_response = client.get("/map/workspaces/1/observations.geojson")
    assert geojson_response.status_code == 200
    feature = geojson_response.json()["features"][0]
    assert feature["geometry"]["type"] == "Polygon"
    assert feature["properties"]["photos"][0]["thumbnail_url"] == (
        "https://example.com/nettle-thumb.jpg"
    )


def test_frontend_index_served(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Crop Oracle" in response.text
