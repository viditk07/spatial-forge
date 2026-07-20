from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFilter
from sqlalchemy import select

from spatialforge_backend.db.models import CaptureDevice, Project
from spatialforge_backend.services.images import _gps_coordinate


def _create_project(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/projects", json={"name": "Image Test", "project_type": "single_room"}
    )
    assert response.status_code == 201
    return response.json()


def _fixture(path: Path, *, shift: int = 0) -> None:
    image = Image.new("RGB", (1800, 1800), (70, 90, 110))
    draw = ImageDraw.Draw(image)
    for index in range(0, 1800, 90):
        draw.line((index + shift, 0, 1800 - index, 1800), fill=(220, 210, 190), width=8)
    image.save(path, "JPEG", quality=92)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_exif_gps_coordinate_conversion_is_direction_aware() -> None:
    assert _gps_coordinate((12, 30, 0), "N") == 12.5
    assert _gps_coordinate((77, 15, 0), "W") == -77.25
    assert _gps_coordinate((12, 0), "N") is None
    assert _gps_coordinate((12, 30, 0), "invalid") is None


def test_import_records_exif_capture_device(client: TestClient, tmp_path: Path) -> None:
    project = _create_project(client)
    source = tmp_path / "camera.jpg"
    exif = Image.Exif()
    exif[271] = "Fixture Phone Company"
    exif[272] = "Fixture Phone 1"
    exif[42036] = "Main Camera 24mm"
    Image.new("RGB", (1800, 1800), (70, 90, 110)).save(source, "JPEG", exif=exif)

    response = client.post(
        f"/api/v1/projects/{project['id']}/images/import", json={"paths": [str(source)]}
    )
    assert response.status_code == 201, response.text
    factory = client.app.state.session_factory
    with factory() as session:
        stored_project = session.get(Project, project["id"])
        device = session.scalar(select(CaptureDevice))
        assert stored_project is not None and device is not None
        assert stored_project.capture_device_id == device.id
        assert device.manufacturer == "Fixture Phone Company"
        assert device.lens_model == "Main Camera 24mm"


def test_import_preserves_original_and_creates_derivatives(
    client: TestClient, tmp_path: Path
) -> None:
    project = _create_project(client)
    source = tmp_path / "phone.jpg"
    _fixture(source)
    before = _digest(source)

    response = client.post(
        f"/api/v1/projects/{project['id']}/images/import",
        json={"paths": [str(source)], "remove_gps_from_working_copies": True},
    )
    assert response.status_code == 201, response.text
    body = response.json()[0]
    assert body["original_filename"] == "phone.jpg"
    assert (body["width"], body["height"]) == (1800, 1800)
    root = Path(str(project["root_path"]))
    originals = list((root / "originals").iterdir())
    assert len(originals) == 1
    assert _digest(source) == before == _digest(originals[0])
    assert len(list((root / "working_images").iterdir())) == 1
    assert len(list((root / "thumbnails").glob("*.jpg"))) == 1


def test_analysis_groups_exact_duplicates_and_supports_exclusion(
    client: TestClient, tmp_path: Path
) -> None:
    project = _create_project(client)
    first = tmp_path / "first.jpg"
    second = tmp_path / "second.jpg"
    _fixture(first)
    second.write_bytes(first.read_bytes())
    imported = client.post(
        f"/api/v1/projects/{project['id']}/images/import",
        json={"paths": [str(first), str(second)]},
    )
    assert imported.status_code == 201

    analysed = client.post(f"/api/v1/projects/{project['id']}/images/analyse")
    assert analysed.status_code == 200, analysed.text
    images = analysed.json()
    assert all(item["quality_metric"]["blur_score"] > 0 for item in images)
    assert all(item["quality_metric"]["feature_count_estimate"] > 0 for item in images)
    assert {item["quality_status"] for item in images} == {"exclude_recommended"}
    groups = {item["quality_metric"]["duplicate_group_id"] for item in images}
    assert len(groups) == 1
    assert None not in groups
    assert all(item["quality_metric"]["duplicate_similarity"] == 1.0 for item in images)

    updated = client.patch(f"/api/v1/images/{images[0]['id']}", json={"included": False})
    assert updated.status_code == 200
    assert updated.json()["included"] is False
    assert len(list((Path(str(project["root_path"])) / "originals").iterdir())) == 2


def test_corrupt_image_does_not_leave_partial_files(client: TestClient, tmp_path: Path) -> None:
    project = _create_project(client)
    corrupt = tmp_path / "broken.jpg"
    corrupt.write_bytes(b"not an image")
    response = client.post(
        f"/api/v1/projects/{project['id']}/images/import", json={"paths": [str(corrupt)]}
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNSUPPORTED_IMAGE_FORMAT"
    root = Path(str(project["root_path"]))
    assert list((root / "originals").iterdir()) == []
    assert client.get(f"/api/v1/projects/{project['id']}/images").json() == []


def test_analysis_groups_transitive_near_duplicates(client: TestClient, tmp_path: Path) -> None:
    project = _create_project(client)
    paths = []
    for index, shift in enumerate((0, 1, 2)):
        path = tmp_path / f"near-{index}.jpg"
        _fixture(path, shift=shift)
        paths.append(str(path))
    imported = client.post(f"/api/v1/projects/{project['id']}/images/import", json={"paths": paths})
    assert imported.status_code == 201, imported.text

    analysed = client.post(f"/api/v1/projects/{project['id']}/images/analyse")

    assert analysed.status_code == 200, analysed.text
    images = analysed.json()
    groups = {item["quality_metric"]["duplicate_group_id"] for item in images}
    assert len(groups) == 1
    assert None not in groups
    assert all(item["quality_metric"]["duplicate_similarity"] >= 0.94 for item in images)


def test_focus_score_ranks_sharp_fixture_above_blurred_fixture(
    client: TestClient, tmp_path: Path
) -> None:
    project = _create_project(client)
    sharp = tmp_path / "sharp.jpg"
    blurred = tmp_path / "blurred.jpg"
    _fixture(sharp)
    with Image.open(sharp) as image:
        image.filter(ImageFilter.GaussianBlur(radius=12)).save(blurred, "JPEG", quality=92)
    imported = client.post(
        f"/api/v1/projects/{project['id']}/images/import",
        json={"paths": [str(sharp), str(blurred)]},
    )
    assert imported.status_code == 201, imported.text

    analysed = client.post(f"/api/v1/projects/{project['id']}/images/analyse")

    assert analysed.status_code == 200, analysed.text
    scores = {
        item["original_filename"]: item["quality_metric"]["blur_score"] for item in analysed.json()
    }
    assert scores["sharp.jpg"] > scores["blurred.jpg"] * 2


def test_import_and_analysis_handles_eighty_photos(client: TestClient, tmp_path: Path) -> None:
    project = _create_project(client)
    paths: list[str] = []
    for index in range(80):
        path = tmp_path / f"capture-{index:03}.jpg"
        image = Image.new("RGB", (96, 96), ((index * 17) % 255, 80, 140))
        ImageDraw.Draw(image).line((0, index % 96, 95, (index * 7) % 96), fill="white", width=2)
        image.save(path, "JPEG", quality=80)
        paths.append(str(path))

    imported = client.post(
        f"/api/v1/projects/{project['id']}/images/import",
        json={"paths": paths},
    )
    assert imported.status_code == 201, imported.text
    assert len(imported.json()) == 80

    analysed = client.post(f"/api/v1/projects/{project['id']}/images/analyse")
    assert analysed.status_code == 200, analysed.text
    assert len(analysed.json()) == 80
