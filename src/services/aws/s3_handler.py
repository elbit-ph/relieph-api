import boto3
import os
from dotenv import load_dotenv
from fastapi import UploadFile
from PIL import Image
from typing import List

load_dotenv()

# NOTE: use `aws configure` to set access keys
class S3_Handler():
    def __init__(self):
        #configure stuff here
        #self.bucket_name = os.environ.get('S3_BUCKET_NAME')
        self.s3 = boto3.client('s3')
        self.bucket_name = 'elbit-relieph'
        self.allowed_directories = ('users', 'organizations', 'relief-efforts', 'updates')
        self.allowed_img_suffix = ('png', 'jpg')
        
        self.s3_direct_session = boto3.Session(aws_access_key_id=os.environ.get('AWS_ACCESS_KEY_ID'), aws_secret_access_key=os.environ.get('AWS_SECRET_ACCESS_KEY'))
        self.s3_direct_bucket = self.s3_direct_session.resource('s3')
        self.s3_bucket = self.s3_direct_bucket.Bucket(os.environ.get('S3_BUCKET_NAME'))

    # get link of image
    def get_image(self, id:int, from_:str) -> str:
        if from_ not in self.allowed_directories:
            return ('InvalidDirectory', False)
        to_return = ""
        for obj in self.s3_bucket.objects.filter(Prefix=f'{from_}/'):
            print(obj.key.split('/')[-1].split('.')[0])
            if (obj.key.split('/')[-1].split('.')[0] == str(id)):
                print(obj.key)
                to_return = obj.key
                break

        if to_return == "":
            return ('NonExistentImage', False)
        
        # return presigned url
        presigned_url = ""
        try:
            response = self.s3.generate_presigned_url('get_object',
                                                 Params={'Bucket':os.environ.get('S3_BUCKET_NAME'),
                                                         'Key' : to_return},
                                                 ExpiresIn=3600)
            presigned_url = response
        except:
            return ('ErrorPresigning', False)

        return (presigned_url, True)
    
    async def upload_multiple(self, images: List[UploadFile], id:int, to:str):
        # if to not in self.allowed_directories:
        #     return ('InvalidDirectory', False)
        to_upload = []
        try:
            count = 1
            for image in images:
                suffix = image.filename.split('.')[-1]
                if suffix not in self.allowed_img_suffix:
                    # if not valid image file, return error
                    return ('InvalidImage', False)
                # process and add image to list of to_upload
                image.filename = f'{count}.{suffix}'
                count += 1
                to_upload.append(image)
            
            for image in to_upload:
                self.s3.upload_fileobj(image.file, self.bucket_name, f'{to}/{image.filename}')
        
        except Exception as e:
            return ('UploadError', False)
        return ('Success', True)
    
    async def retrieve_multiple(self, id:int, from_:str):
        # validate `from_` if valid source
        
        # iteratively return all links of images in folder
        to_return = []
        for obj in self.s3_bucket.objects.filter(Prefix=f'{from_}/'):
            #print(obj.key)
            to_return.append(obj.key)
    
        if len(to_return) == 0:
            return ("ImagesNonExistent", False)
            
        image_urls = []
        for key in to_return:
            try:
                response = self.s3.generate_presigned_url('get_object',
                                                 Params={'Bucket':os.environ.get('S3_BUCKET_NAME'),
                                                         'Key' : key},
                                                 ExpiresIn=3600)
                # check if response is valid?
                image_urls.append(response)
            except:
                return ('ErrorPresigning', False)

        return (image_urls, True)
    
    # uploads user profile
    async def upload_single_image(self, file: UploadFile, id:int, to:str):
        if to not in self.allowed_directories:
            return ('InvalidDirectory', False)
        try:
            suffix = file.filename.split('.')[-1]
            if (suffix not in self.allowed_img_suffix):
                # if not valid image file, return error
                return ('InvalidImage', False)
            # NOTE: try to change to png
            file.filename = f'{id}.{suffix}'
            self.s3.upload_fileobj(file.file, self.bucket_name, f'{to}/{file.filename}')
        except:
            return ('FailedUpload',False)
        return ('Success', True)

    async def delete_image(self, id:int, from_:str):
        if from_ not in self.allowed_directories:
            return ('InvalidDirectory', False)
        to_delete = ""
        
        for obj in self.s3_bucket.objects.filter(Prefix=f'{from_}/'):
            print(obj.key.split('/')[-1].split('.')[0])
            if (obj.key.split('/')[-1].split('.')[0] == str(id)):
                print(obj.key)
                to_delete = obj.key
                break

        if to_delete == "":
            return ('NonExistentImage', False)

        self.s3.delete_object(Bucket=self.bucket_name, Key=to_delete)
        
        return ('Success', True)