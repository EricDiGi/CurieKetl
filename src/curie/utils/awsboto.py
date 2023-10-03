import boto3
import os
import sys
import base64

class Secrets:
    def __init__(self, secretId) -> None:
        self.secretId_ = secretId
        self.__get_secret()
    
    def __get_secret(self):
        """
        returns a dictionary of secrets
        """
        try:
            client = boto3.client('secretsmanager')
            response = client.get_secret_value(SecretId=self.secretId_)
        except:
            print("Unexpected error:", sys.exc_info()[0])
            raise
        else:
            if 'SecretString' in response:
                secret = response['SecretString']
            else:
                secret = base64.b64decode(response['SecretBinary'])
        return secret