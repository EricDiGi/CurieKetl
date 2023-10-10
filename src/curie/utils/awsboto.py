import boto3
import os
import sys
import base64

class Secrets:
    def __init__(self, secretId, region) -> None:
        self.secretId_ = secretId
        self.region_ = region
        self.__get_secret()
    
    def __get_secret(self):
        """
        returns a dictionary of secrets
        """
        try:
            client = boto3.client('secretsmanager', region_name=self.region_)
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
    
    @property
    def secret(self):
        return self.__get_secret()

class CFN:
    def __init__(self, stackName, region) -> None:
        self.stackName_ = stackName
        self.region_ = region
        self.sm_value = self.__get_stack()
        self.sm = Secrets(self.sm_value, self.region_)
        self.value = self.sm.secret
    
    def __get_stack(self):
        """
        returns a dictionary of stack outputs
        """
        try:
            client = boto3.client('cloudformation', region_name=self.region_)
            response = client.list_exports()
            try:
                exports = response['Exports']
                export = list(filter(lambda x: x['Name'] == self.stackName_, exports))[0]
                self.value = export['Value']
                return self.value
            except:
                self.value = None
                raise
        except:
            print("Unexpected error:", sys.exc_info()[0])
            raise
    
    @property
    def secret(self):
        return self.__get_stack()
        