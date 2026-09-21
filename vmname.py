import requests

IMDS_URL = (
    "http://169.254.169.254/metadata/instance/compute"
    "?api-version=2025-04-07"
)

def get_vm_metadata():
    response = requests.get(
        IMDS_URL,
        headers={"Metadata": "true"},
        proxies={"http": None, "https": None},
        timeout=5,
    )
    response.raise_for_status()

    compute = response.json()

    return compute

vmname = get_vm_metadata()
print(vmname)
