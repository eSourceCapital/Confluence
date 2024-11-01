from google.cloud import storage

async def delete_files_in_bucket(bucket_name):
    try:
        # Conexión a Google Cloud Storage
        client = storage.Client()
        bucket = client.bucket(bucket_name)
    
        blobs = bucket.list_blobs()  # Listar todos los archivos en el bucket

        for blob in blobs:
            blob.delete()  # Eliminar archivo
            print(f'File {blob.name} deleted from bucket {bucket_name}.')
    except Exception as e:
        return {"status":-1 , "msg":"Unknown", "data":e}