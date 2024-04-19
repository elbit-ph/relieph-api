from fastapi import UploadFile

def is_image_valid(image: UploadFile):
    suffix = image.filename.split('.')[-1]
    if suffix not in ('png', 'jpg'):
        # if not valid image file, return error
        return False
    # process and add image to list of to_upload
    return True