import os
from dotenv import load_dotenv
from minio import Minio
from minio.commonconfig import SnowballObject
from minio.deleteobjects import DeleteObject
from typing import List
from fastapi import UploadFile

load_dotenv()

class FileHandler():
    def __init__(self):
        self.allowed_directories = ('users', 'organizations', 'relief-efforts', 'updates')
        self.allowed_img_suffix = ('png', 'jpg')
        self.bucket_name = 'relieph' # place in .env later
        self.handler:Minio = Minio(endpoint=os.environ.get('MINIO_URI'),
            access_key=os.environ.get('MINIO_ACCESS_KEY'),
            secret_key=os.environ.get('MINIO_SECRET_KEY'),
            secure=False
        )
    
    # checks existence of particular file
    def is_file_existent(self, filename:str):
        if self.handler.get_object(self.bucket_name, filename) == None:
            # file non-existent
            return False
        return True

    # retrieves file from object store
    def retrieve_file(self, id:int, from_:str):
        if from_ not in self.allowed_directories:
            return ('InvalidDirectory', False)
        to_return = ""

        # iterate thru object store for file
        for obj in self.handler.list_objects(self.bucket_name, prefix=from_, recursive=True):
            if obj.object_name.split('/')[-1].split('.')[0] == str(id):
                print(obj.object_name)
                to_return = obj.object_name
                break

        if to_return == "":
            return ('NonExistentFile', False)
        
        # return presigned url
        presigned_url = self.handler.presigned_get_object(self.bucket_name, obj.object_name)

        return (presigned_url, True)
    
    # retrieve multiple files
    def retrieve_files(self, id:int, from_:str):
        dir_to_return = ""
        
        # find directory to return
        for obj in self.handler.list_objects(self.bucket_name, prefix=f'{from_}/'):
            if obj.object_name[-1] != '/': # not a directory
                continue
            if obj.object_name.split('/')[-2] == str(id):
                dir_to_return = obj.object_name
                break

        if dir_to_return == "":
            return ("NoDirectoryFound", False)

        files_to_return = []
        for obj in self.handler.list_objects(self.bucket_name, prefix=f'{from_}/{id}', recursive=True):
            # add presigned url to list of images
            files_to_return.append(self.handler.presigned_get_object(self.bucket_name, obj.object_name))

        if len(files_to_return) == 0:
            return ("NoImagesFound", False)

        return files_to_return
    
    # upload a single file
    async def upload_file(self, file:UploadFile, id:int, to:str):
        
        if to not in self.allowed_directories:
            return ('InvalidDirectory', False)
        
        try:
            # handle file checking outside this function
            suffix = file.filename.split('.')[-1]
            file.filename = f'{id}.{suffix}'
            self.handler.put_object(
                bucket_name=self.bucket_name,
                object_name=f'{to}/{file.filename}',
                data=file.file,
                length=file.file.__sizeof__()
            )

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
                to_upload.append(SnowballObject(
                    object_name=f'{to}/{id}/{file.filename}',
                    filename=file.filename,
                    data=file.file,
                    length=file.file.__sizeof__()
                ))
                count += 1

            self.handler.upload_snowball_objects(
                self.bucket_name,
                to_upload)

        except:
            return ('UploadError', False)
        
        return ('Success', True)
    
    # deletes a single image
    async def remove_file(self, id:int, from_:str):
        if from_ not in self.allowed_directories:
            return ('InvalidDirectory', False)
        to_delete = ""

        # iterate thru object store for file
        for obj in self.handler.list_objects(self.bucket_name, prefix=from_, recursive=True):
            if obj.object_name.split('/')[-1].split('.')[0] == str(id):
                print(obj.object_name)
                to_delete = obj.object_name
                break

        if to_delete == "":
            return ('NonExistentFile', False)
        
        self.handler.remove_object(self.bucket_name, to_delete)
        
        return ('Success', True)
    
    # delete multiple files
    def remove_files(self, id:int, from_:str):
        dir_to_return = ""
        
        # find directory to return
        for obj in self.handler.list_objects(self.bucket_name, prefix=f'{from_}/'):
            if obj.object_name[-1] != '/': # not a directory
                continue
            if obj.object_name.split('/')[-2] == str(id):
                dir_to_return = obj.object_name
                break

        if dir_to_return == "":
            return ("NoDirectoryFound", False)
        
        to_remove = []
        
        # creates list of items to delete
        for obj in self.handler.list_objects(self.bucket_name, prefix=f'{from_}/{id}', recursive=True):
            to_remove.append(DeleteObject(obj.object_name))
        
        self.handler.remove_objects(self.bucket_name, to_remove)

        return ('Success', True)
    
    def is_file_valid(self, file:UploadFile, allowed_suffixes:List[str]):
        if file.filename.split('.')[-1] not in allowed_suffixes:
            # suffix is not in allowed suffixes
            return False
        return True
    
    def are_files_valid(self, files:List[UploadFile], allowed_suffixes:List[str]):
        for file in files:
            if file.filename.split('.')[-1] not in allowed_suffixes:
                # suffix is not in allowed suffixes
                return False
            
        return True
    
    def get_user_profile(self, id:int):
        resu = self.retrieve_file(id, 'users')
        if resu[1] == False:
            # default = self.handler.get_object(self.bucket_name, 'users/default_profile.png')
            return self.handler.presigned_get_object(self.bucket_name, 'users/default_profile.png')
        return resu[0]