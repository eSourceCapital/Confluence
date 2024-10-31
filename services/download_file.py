import requests
import re
import os
import time
from services.confluence_api import get_confluence_page_title_by_id, is_empty_confluence_page, get_pdf_export_confluence_url
import time
from google.cloud import storage
import io

def download_pdf_from_presigned_url(url, output_path):
    """
    Authenticates with a server to retrieve a pre-signed URL and downloads a file.

    Args:
        url (str): URL for download request
        output_path (str): Path, including filename, where PDF should be downloaded
        
    Return:
        Status code. 200 is succesful
    """
    #Get path and filename
    directory = os.path.dirname(output_path)
    if not os.path.exists(directory):
        os.makedirs(directory)

    #Make sure filename ends in .pdf
    filename = os.path.basename(output_path)
    if not filename.lower().endswith('.pdf'):
        filename += '.pdf'
    output_path = f"{directory}/{filename}"
        
    response = requests.get(url, stream=True)
    
    if response.status_code == 200:
        with open(output_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                file.write(chunk)
        print(f"File downloaded successfully and saved as {filename}")  
    else:
        print(f"Failed to download {filename}. Status code: {response.status_code}")
    
    return {"statusCode": response.status_code}    

def download_pdf_from_presigned_url_to_gcs_bucket(url, filename, gcs_bucket_name):
    """
    Downloads a PDF from a pre-signed URL directly to a Google Cloud Storage bucket.

    Args:
        url (str): URL for download request
        filename (str): Name of file in the GCS bucket
        gcs_bucket_name (str): Google Cloud Storage bucket to upload the file to
        
    Returns:
        Status code of the download request. 200 is successful.
    """
    
    # Make sure filename is properly formatted and ends in .pdf
    filename = convert_title_to_filename(filename)
    if not filename.lower().endswith('.pdf'):
        filename += '.pdf'
        
    # Perform the request to get the file content
    response = requests.get(url, stream=True)
    
    if response.status_code == 200:
        # Initialize the Google Cloud Storage client
        storage_client = storage.Client()
        bucket = storage_client.bucket(gcs_bucket_name)
        blob = bucket.blob(filename)
        
        # Use an in-memory BytesIO buffer to hold the file content temporarily
        with io.BytesIO() as file_buffer:
            for chunk in response.iter_content(chunk_size=8192):
                file_buffer.write(chunk)
            
            # Reset buffer position to the beginning
            file_buffer.seek(0)
            
            # Upload directly from the buffer
            blob.upload_from_file(file_buffer, content_type='application/pdf')
        
        print(f"File downloaded successfully and saved to GCS bucket {gcs_bucket_name} as {filename}")
    
    else:
        print(f"Failed to download {filename}. Status code: {response.status_code}")
    
    return {"statusCode": response.status_code}
      
def convert_title_to_filename(title):
    """
    Converts a title string to a safe filename format by replacing spaces with underscores
    and removing non-word characters.

    Args:
        title (str): The title to be converted.

    Returns:
        str: The converted filename with spaces replaced by underscores and non-word characters removed.
    """
    return re.sub(r'\W+', '', title.strip().replace(' ', '_'))
  
def export_pdf_confluence_page_by_id(
    domain, 
    email, 
    api_token, 
    page_id, 
    page_title=None, 
    output_path=None, 
    gcs_bucket_name=None,
    wait_time=15):
    
    """
    Exports a page as a PDF from the Confluence API.
    Args:
        domain (str): The Confluence instance domain (e.g., 'your-domain.atlassian.net').
        email (str): The email address of the Confluence user.
        api_token (str): The API token for authentication.
        page_id (str): The ID of the page to fetch details for.
        page_title (str): The title of the page to fetch details for. Optional.
        output_path (str): Path where file will be downloaded to. Optional. 
                           Default is 'confluence_downloads/'
        gcs_bucket (str): Google Cloud Storage bucket to upload the file to. Optional.

    Returns:
        str: Status of the downloaded page: 'EMPTY_PAGE', 'DOWNLOAD_SUCCESFUL', 'DOWNLOAD_FAILED'
    """
    
    #Get page title if not provided
    if not page_title:
        page_title = get_confluence_page_title_by_id(domain, email, api_token, page_id)
    
    #File page title, formatted and ending in confluencePageId=page_id   
    file_page_title = f"{convert_title_to_filename(page_title)}_confluencePageId={page_id}"
    
    #Check if it is an empty page
    if is_empty_confluence_page(domain, email, api_token, page_id):
        print(f"{file_page_title} is an empty page.")
        return 'EMPTY_PAGE'

    #Try 3 times
    for attempt in range(3):
        #Generate the presigned download URL
        url = get_pdf_export_confluence_url(domain, email, api_token, page_id)
        
        #To avoid file not found error, wait a bit before downloading from the URL
        time.sleep(wait_time)
        
        #Download the file, and store the status code
        
        #If there is a bucket specified, download to bucket
        if gcs_bucket_name:    
            download_url = download_pdf_from_presigned_url_to_gcs_bucket(url=url, filename=file_page_title, gcs_bucket_name=gcs_bucket_name)
            status_code = download_url['statusCode']
            
        #If not, download to output_path
        else: 
            #If no output_path, then set to a value
            if not output_path:
                output_path = 'confluence_downloads/'
            #Make sure output_path ends in /
            output_path = output_path + "/" if not output_path.endswith("/") else output_path
        
            status_code = download_pdf_from_presigned_url(url=url, output_path=f"{output_path}{file_page_title}")  
        
        if status_code == 200:
            return 'DOWNLOAD_SUCCESFUL'
        else:
            wait_time += 10 #Increase wait between url and download
            print(f"Attempt {attempt + 1} failed with status code {status_code}. Retrying in 10 seconds...")
            time.sleep(10)
            
    return 'DOWNLOAD_FAILED'