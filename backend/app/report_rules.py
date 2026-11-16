from decimal import Decimal


def conformity(download, upload, service_download, service_upload, percent):
    """No guessed percentage, symmetric SLA or missing result becomes a pass."""
    if any(value is None for value in (service_download, service_upload, percent)):
        return None, 'profile_missing'
    if any(value is None for value in (download, upload)):
        return None, 'measurement_missing'
    ratio = Decimal(str(percent)) / Decimal('100')
    matches = Decimal(str(download)) >= Decimal(str(service_download)) * ratio and Decimal(str(upload)) >= Decimal(str(service_upload)) * ratio
    return ('conforming' if matches else 'not_conforming'), 'calculated'


def site_report(report, site):
    """Server supplies the identity/policy and computes both backbone decisions."""
    result = report.model_dump()
    result['customer_company'] = site.customer_name or site.name
    profile = site.maintenance_profile or {}
    result['site_profile'] = profile
    percent = profile.get('minimum_percent')
    for key in ('fo', 'wireless'):
        branch = result.get(key)
        if branch is None:
            continue
        service = profile.get(key) or {}
        branch['agreement_download_mbps'] = service.get('download_mbps')
        branch['agreement_upload_mbps'] = service.get('upload_mbps')
        branch['minimum_percent'] = percent
        branch['conformity'], branch['conformity_reason'] = conformity(
            branch['download_mbps'], branch['upload_mbps'],
            branch['agreement_download_mbps'], branch['agreement_upload_mbps'], percent)
        for legacy in ('agreement_mbps', 'speedtest_mbps', 'tx_mbps', 'rx_mbps', 'ccq_percent'):
            if branch.get(legacy) is None:
                branch.pop(legacy, None)
    return result
