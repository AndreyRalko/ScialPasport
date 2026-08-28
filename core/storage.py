from storages.backends.s3boto3 import S3Boto3Storage


class MinioMediaStorage(S3Boto3Storage):
    location = "media"
    file_overwrite = False
    default_acl = None
    querystring_auth = False
    addressing_style = "path"
