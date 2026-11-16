"""Validate staging opt-in guards without making database connections."""
import pytest
from test_staging import validate_staging_url


@pytest.mark.parametrize('url', [
    'postgresql+psycopg://localhost/hotel_maintenance',
    'sqlite:///hotel_test',
    'postgresql://localhost/hotel_test',
    'postgresql+psycopg://localhost/hotel_test?dbname=production',
    'postgresql+psycopg://localhost/hotel_test?options=-csearch_path=public',
])
def test_reject_unsafe_staging_configuration(url):
    with pytest.raises(ValueError):
        validate_staging_url(url)


def test_accept_dedicated_staging_database():
    assert validate_staging_url('postgresql+psycopg://localhost/hotel_staging').database == 'hotel_staging'
