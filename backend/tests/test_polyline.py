import pytest

from routing.polyline import decode


def test_decodes_the_reference_example():
    points = decode("_p~iF~ps|U_ulLnnqC_mqNvxq`@", precision=5)
    assert points == pytest.approx([(38.5, -120.2), (40.7, -120.95), (43.252, -126.453)])


def test_empty_string_has_no_points():
    assert decode("") == []
