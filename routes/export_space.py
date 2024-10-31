from services.confluence_api import get_confluence_space_id_by_key, get_confluence_homepage_id_by_space_id, get_confluence_children_by_parent_page_id_recursive
from services.download_file import export_pdf_confluence_page_by_id
from services.delete_files import delete_files_in_bucket
from google.cloud import storage
import os
from fastapi import APIRouter
from fastapi import status
from dotenv import load_dotenv

# Load the stored environment variables
load_dotenv()

reqExportSpace = APIRouter()

@reqExportSpace.post(
    path="/export_space",
    status_code=status.HTTP_200_OK,
    summary="Endpoint to delete GCS bucket and download a Confluence space as PDFs"
)   

async def export_pdf_confluence_space_to_gcs_bucket_by_key():
    """
    Exports all pages in a space as a PDF from the Confluence API.
    
    Requires from env variables:
        domain (str): The Confluence instance domain (e.g., 'your-domain.atlassian.net').
        email (str): The email address of the Confluence user.
        api_token (str): The API token for authentication.
        space_key (str): The key of the space to fetch details for (e.g. 'OR' your-domain.atlassian.atlassian.net/wiki/spaces/OR/).
        output_path (str): Path where file will be downloaded to.

    Returns:
        dict JSON response, where data = pages_status. Keys: Page IDs, and Values: Status of the downloaded page: 'EMPTY_PAGE', 'DOWNLOAD_SUCCESFUL', 'DOWNLOAD_FAILED'
    """
    
    try:
        domain = os.getenv('DOMAIN')
        email = os.getenv('EMAIL')
        api_token = os.getenv('API_TOKEN')
        space_key = os.getenv('SPACE_KEY')
        gcs_bucket_name = os.getenv('GCS_BUCKET_NAME')
        wait_time = int(os.getenv('WAIT_TIME_BEFORE_DOWNLOAD'))
        print(f"Succesfully loaded environment variables: domain = {domain}, email = {email}, api_token is secret, space_key = {space_key}, gcs_bucket_name = {gcs_bucket_name} and wait_time (before downloading file from URL) = {wait_time}")
        
    except:
        return {"status":-1 , "msg":"Could not load environment variables", "data":str(e)}
    
    try:
        await delete_files_in_bucket(gcs_bucket_name)
        storage_client = storage.Client()
        storage_client.bucket(gcs_bucket_name)
        print(f"Bucket {gcs_bucket_name} cleaned succesfully.")
    
    except Exception as e:
        return {"status":-1 , "msg":"Could not clean bucket", "data":str(e)}
    
    try: 
        print(f"Starting Confluence space download as PDF...")
        #Get space id
        space_id = get_confluence_space_id_by_key(domain, email, api_token, space_key)
        print(f"Space ID: {space_id}")

        #Get homepage id
        homepage_id = get_confluence_homepage_id_by_space_id(domain, email, api_token, space_id)
        print(f"Homepage ID: {homepage_id}")

        #Get all children from the homepage
        pages_ids_dict = get_confluence_children_by_parent_page_id_recursive(domain, email, api_token, homepage_id)
        print(f"Page IDs and titles: {pages_ids_dict}")
        
        #Store status of pages
        pages_status = {}
        
        #Download pages
        for page_id, page_title in pages_ids_dict.items():
            #Download page
            page_status = export_pdf_confluence_page_by_id(
                domain=domain, 
                email=email, 
                api_token=api_token, 
                page_id=page_id, 
                page_title=page_title,
                output_path=None, 
                gcs_bucket_name=gcs_bucket_name,
                wait_time=wait_time)
            
            if page_status not in pages_status:
                pages_status[page_status] = [page_id]
            else:
                pages_status[page_status].append(page_id)
            
        print(pages_status)
        return {"status": 1 , "msg":"Confluence space download succesful", "data": pages_status}
    
    except Exception as e:
        return {"status": -1 , "msg": "Confluence space download failed", "data": f"Exception of {type(e)}: {e}"}