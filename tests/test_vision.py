import numpy as np

from orca.vision import DemoCamera, DemoOCR, annotate_regions, image_data_url


def test_demo_ocr_returns_boxed_region():
    frame = DemoCamera().read()
    result = DemoOCR().read(frame)
    annotated = annotate_regions(frame, result.regions)
    assert result.text == "ORCA demo product 20"
    assert len(result.regions[0].polygon) == 4
    assert not np.array_equal(frame, annotated)
    assert image_data_url(annotated).startswith("data:image/jpeg;base64,")

