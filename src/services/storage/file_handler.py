import os
import cloudinary.search
import cloudinary.search_folders
from dotenv import load_dotenv
from typing import List
from fastapi import UploadFile
import cloudinary
import cloudinary.uploader
import cloudinary.api

load_dotenv()

class FileHandler():
    def __init__(self):
        self.allowed_directories = ('users', 'organizations', 'relief-efforts', 'updates', 'valid_ids')
        self.allowed_img_suffix = ('png', 'jpg')
        cloudinary.config(
            cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'),
            api_key = os.environ.get('CLOUDINARY_API_KEY'),
            api_secret = os.environ.get('CLOUDINARY_SECRET'),
            secure=True
        )

    # retrieves file from object store
    async def retrieve_file(self, id:int, from_:str):
        if from_ not in self.allowed_directories:
            return ('InvalidDirectory', False)

        filename=f"relieph/{from_}/{id}"

        if self.file_exists(filename, from_) == False:
            return ('NonExistentFile', False)
        image_link = None
        try:
            image_link = cloudinary.api.resource(filename)['secure_url']
        except Exception as e:
            return ('ErrorRetrieving', False)
        return (image_link, True)
    
    # retrieve multiple files
    async def retrieve_files(self, id:int, from_:str):
        resu = None

        try:
            resu = cloudinary.api.resources(type='upload',prefix=f"relieph/{from_}/{id}")
        except Exception as e:
            return ('ErrorRetrievingFiles', False)

        # extract only `secure_url`
        parsed_resu = map(lambda image: image['secure_url'] ,resu['resources'])
        
        return (list(parsed_resu), True)

    # upload a single file
    async def upload_file(self, file:UploadFile, id:int, to:str):
        
        if to not in self.allowed_directories:
            return ('InvalidDirectory', False)
        
        try:
            # handle file checking outside this function
            suffix = file.filename.split('.')[-1]
            file.filename = f'{id}.{suffix}'
            cloudinary.uploader.upload(file.file, public_id=f"relieph/{to}/{id}")

        except Exception as e:
            print(e)
            return ('FailedUpload', False)

        return ('Success', True)

    # upload multiple file under `id` folder
    async def upload_multiple_file(self, files: List[UploadFile], id: int, to:str):
        try:
            to_upload = []

            count = 1
            # iterate thru uploaded files
            for file in files:
                suffix = file.filename.split('.')[-1]
                file.filename = f'{count}.{suffix}'
                cloudinary.uploader.upload(file.file, public_id=f"relieph/{to}/{id}/{file.filename}")
                count += 1

        except:
            return ('UploadError', False)
        
        return ('Success', True)
    
    # deletes a single image
    async def remove_file(self, id:int, from_:str):
        try:
            cloudinary.uploader.destroy(f"relieph/{from_}/{id}")
        except Exception as e:
            return ('ErrorDeleting', False)
        
        return ('Success', True)
    
    # delete multiple files
    def remove_files(self, id:int, from_:str):
        try:
            cloudinary.api.delete_resources_by_prefix(f"{from_}/{id}")
        except Exception as e:
            return ('ErrorDeleting', False)
        
        return ('Success', True)
    
    async def is_file_valid(self, file:UploadFile, allowed_suffixes:List[str]):
        if file.filename.split('.')[-1] not in allowed_suffixes:
            # suffix is not in allowed suffixes
            return False
        return True
    
    async def are_files_valid(self, files:List[UploadFile], allowed_suffixes:List[str]):
        for file in files:
            if file.filename.split('.')[-1] not in allowed_suffixes:
                # suffix is not in allowed suffixes
                return False
            
        return True
    
    async def file_exists(self, id:int, from_:str):
        try:
            # try getting file
            image = cloudinary.api.resource(f"relieph/{from_}/{id}")
        except Exception as e:
            return False
        return True
    
    async def get_user_profile(self, id:int):
        resu = await self.retrieve_file(id, 'users')
        if resu[1] == False:
            return cloudinary.api.resource('relieph/users/default_profile')['secure_url']
        return resu[0]
    
    async def get_org_profile(self, id:int):
        resu = await self.retrieve_file(id, 'organizations')
        if resu[1] == False:
            return cloudinary.api.resource('relieph/organizations/default_profile')['secure_url']
        return resu[0]