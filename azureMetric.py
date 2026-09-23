from azure.identity import DefaultAzureCredential
# from azure.identity import AzureCliCredential
import requests

credential = DefaultAzureCredential()
# credential = AzureCliCredential()


API_URL = (
    "https://management.azure.com/providers/Microsoft.Carbon/"
    "carbonEmissionReports?api-version=2025-04-01"
)


def get_carbon_report(subscription_id, start_date, end_date):
    token = credential.get_token(
        "https://management.azure.com/.default"
    ).token

    body = {
        "reportType": "OverallSummaryReport",

        "subscriptionList": [subscription_id],
        "carbonScopeList": [
            "Scope1",
            "Scope2",
            "Scope3"
        ],
        "dateRange": {
            "start": start_date,
            "end": end_date,
        },
    }

    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=30,
    )

    response.raise_for_status()
    return response.json()


carbonmetrics = get_carbon_report("b4003998-9034-4e5d-86fa-1162338a0a4a", "2026-07-20", "2026-08-20")
 

print(carbonmetrics["value"])