from requests.auth import HTTPBasicAuth
import requests
import re

## CONFLUENCE API

def get_confluence_space_id_by_key(domain: str, email: str, api_token: str, space_key: str) -> dict:
    """
    Fetches space ID details from the Confluence API.

    Args:
        domain (str): The Confluence instance domain (e.g., 'your-domain.atlassian.net').
        email (str): The email address of the Confluence user.
        api_token (str): The API token for authentication.
        space_key (str): The key of the space to fetch details for (e.g. 'OR' your-domain.atlassian.atlassian.net/wiki/spaces/OR/).

    Returns:
        str: The ID of the space provided
    """

    import base64
    auth_string = f"{email}:{api_token}"
    encoded_auth_string = base64.b64encode(auth_string.encode()).decode()
    
    url = f"https://{domain}/wiki/rest/api/space/{space_key}"
    headers = {
        "Authorization": f"Basic {encoded_auth_string}",
        "Accept": "application/json"
    }
    
    response = requests.get(url, headers=headers)
    key_json = handle_json_errors(response)
    return key_json['id']

def get_confluence_homepage_id_by_space_id(domain: str, email: str, api_token: str, space_id: str):
    """
    Fetches a space's homepage ID from the Confluence API.
    Refer to: https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/#api-spaces-id-pages-get
    Args:
        domain (str): The Confluence instance domain (e.g., 'your-domain.atlassian.net').
        email (str): The email address of the Confluence user.
        api_token (str): The API token for authentication.
        space_id (str): The ID of the space to fetch details for.

    Returns:
        s: ID of the homepage
    """
    url = f"https://{domain}/wiki/api/v2/spaces/{space_id}/pages"
    auth = HTTPBasicAuth(email, api_token)
    headers = {
      "Accept": "application/json"
    }
    response = requests.request("GET", url, headers=headers, auth=auth)
    handle_json_errors(response)
    pages = response.json()['results']
    for page in pages:
        if page['parentType'] is None:
            return page['id']
    return None
  
def get_confluence_children_by_parent_page_id_recursive(domain: str, email: str, api_token: str, page_id: str):
    """
    Fetches page's content from the Confluence API.
    Refer to: https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/#api-pages-id-get
    Args:
        domain (str): The Confluence instance domain (e.g., 'your-domain.atlassian.net').
        email (str): The email address of the Confluence user.
        api_token (str): The API token for authentication.
        page_id (str): The ID of the page to fetch content from.

    Returns:
        dict: All page ids and titles
    """
    url = f"https://{domain}/wiki/api/v2/pages/{page_id}/children"
    auth = HTTPBasicAuth(email, api_token)
    headers = {
      "Accept": "application/json"
    }

    response = requests.request("GET", url, headers=headers, auth=auth)
    response.raise_for_status()
    children = response.json()
    if not children or not children['results']:
        return {}

    pages_ids_dict = {}
    for child in children['results']:
        pages_ids_dict[child['id']] = child['title']
        pages_ids_dict.update(get_confluence_children_by_parent_page_id_recursive(domain, email, api_token, child['id']))

    return pages_ids_dict
  
def get_pdf_export_confluence_url(domain, email, api_token, page_id):
    """
    Refer to: https://confluence.atlassian.com/confkb/rest-api-to-export-and-download-a-page-in-pdf-format-1388160685.html
    """
    # Construct the export URL
    url = f"https://{domain}/wiki/spaces/flyingpdf/pdfpageexport.action?pageId={page_id}&unmatched-route=true"
    auth = HTTPBasicAuth(email, api_token)
    headers = {
        "X-Atlassian-Token": "no-check",
    }
    response = requests.get(url, headers=headers, auth=auth, allow_redirects=True)
    task_cloud_ids = extract_task_and_cloud_id_from_html(response.text)
    if task_cloud_ids:
      download_url = f"https://{domain}/wiki/services/api/v1/download/pdf?taskId={task_cloud_ids['taskId']}&cloudId={task_cloud_ids['cloudId']}"
      download_response = requests.get(download_url, auth=HTTPBasicAuth(email, api_token))
      presigned_url = download_response.text
      return presigned_url
  
def get_confluence_page_title_by_id(domain: str, email: str, api_token: str, page_id: str):
    """
    Fetches page title from the Confluence API.
    Refer to: https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/#api-pages-id-get
    Args:
        domain (str): The Confluence instance domain (e.g., 'your-domain.atlassian.net').
        email (str): The email address of the Confluence user.
        api_token (str): The API token for authentication.
        page_id (str): The ID of the page to fetch details for.

    Returns:
        title: page title
    """
    url = f"https://{domain}/wiki/api/v2/pages/{page_id}"
    auth = HTTPBasicAuth(email, api_token)
    headers = {
      "Accept": "application/json"
    }
    response = requests.request("GET", url, headers=headers, auth=auth)
    response = handle_json_errors(response)
    return response['title']
  
def get_confluence_page_content_by_id(domain: str, email: str, api_token: str, page_id: str):
    """
    Fetches page's content from the Confluence API.
    Refer to: https://developer.atlassian.com/cloud/confluence/rest/v2/api-group-page/#api-pages-id-get
    Args:
        domain (str): The Confluence instance domain (e.g., 'your-domain.atlassian.net').
        email (str): The email address of the Confluence user.
        api_token (str): The API token for authentication.
        page_id (str): The ID of the page to fetch content from.

    Returns:
        A string with content of the page
    """
    url = f"https://{domain}/wiki/rest/api/content/{page_id}?expand=body.export_view"
    auth = HTTPBasicAuth(email, api_token)
    headers = {
      "Accept": "application/json"
    }
    response = requests.request("GET", url, headers=headers, auth=auth)
    handle_json_errors(response)
    page_content = response.json()['body']['export_view']['value']
    return page_content

def is_empty_confluence_page(domain: str, email: str, api_token: str, page_id: str):
    """
    Fetches page's content from the Confluence API and checks if it is empty.
    Args:
        domain (str): The Confluence instance domain (e.g., 'your-domain.atlassian.net').
        email (str): The email address of the Confluence user.
        api_token (str): The API token for authentication.
        page_id (str): The ID of the page to fetch content from.

    Returns:
        A  boolean value
    """
    page_content = get_confluence_page_content_by_id(domain, email, api_token, page_id)
    return (page_content == "<p />" or page_content == "")

## HELPER FUNCTIONS

def extract_task_and_cloud_id_from_html(html_string):
    """
    Extracts taskId and cloudId from the meta tags in the HTML string using regular expressions.

    Args:
        html_string: The HTML string to parse.

    Returns:
        A dictionary containing taskId and cloudId, or None if not found.
    """
    # Regular expressions to match the meta tags
    task_id_match = re.search(r'<meta\s+name="ajs-taskId"\s+content="([^"]+)"', html_string)
    cloud_id_match = re.search(r'<meta\s+name="ajs-cloud-id"\s+content="([^"]+)"', html_string)

    task_id = task_id_match.group(1) if task_id_match else None
    cloud_id = cloud_id_match.group(1) if cloud_id_match else None

    if task_id and cloud_id:
        return {'taskId': task_id, 'cloudId': cloud_id}
    else:
        print("taskId or cloudId not found in the HTML")
        return None
  
def handle_json_errors(response):
    """
    Handles JSON parsing for an HTTP response, returning JSON data if successful or error details if not.

    Args:
        response (requests.Response): The HTTP response object to parse.

    Returns:
        dict: A dictionary containing the parsed JSON data if successful,
        or an error message with response details if the JSON parsing fails or if the response status is not 200.
    """
    if response.status_code == 200:
        try:
            data = response.json()
            return data
        except ValueError:
            return {"error": "Response is not JSON formatted", "details": response.text}
    else:
        return {"error": f"Request failed with status {response.status_code}", "details": response.text}