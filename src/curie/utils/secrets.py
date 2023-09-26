import base64
import json
import logging as log
import os

import boto3
import yaml
from botocore.exceptions import ClientError
from dotenv import dotenv_values

from . import ensure_rooting


class EnvironmentFile(dict):
    """
    Loads the environment variables from a file

    Args:
        path (str): The path to the file to load relative to the project root or an absolute path
    
    Returns:
        dict: The environment variables as a dictionary
    """
    def __init__(self, path):
        self.__file = ensure_rooting(path)
        super().__init__(self.__load())
    
    def __load(self):
        if os.path.exists(self.__file):
            return dotenv_values(self.__file)
        else:
            log.error(f'Environment file "{self.__file}" does not exist. Please check your configuration.')
            return {}

class AwsSecretManager(dict): # TODO: implement in the cloud and check that this works
    """
    Load a secret from AWS Secrets Manager

    Args:
        secret_id (str): The name or ARN of the secret to retrieve
        region (str): The region containing the secret
        session (dict): A dictionary containing the session parameters, or an EnvironmentFile object
    
    Returns:
        dict: The secret(s) as a dictionary
    """
    LOCAL_ENV_FILE = 'local.env'
    def __init__(self, secret_id, region, session={}, **kwargs):
        if 'EnvironmentFile' in session:
            session = EnvironmentFile(**session['EnvironmentFile'])
        self.b3session = boto3.session.Session(**session)
        self.invalid = False
        self.client = self.b3session.client('secretsmanager', region_name=region)
        super().__init__(self.get_secret(secret_id))
    
    def get_secret(self, secret_name):
        try:
            response = self.client.get_secret_value(
                SecretId=secret_name
            )
        except ClientError as e:
            raise ValueError(f'Failed to retrieve secret "{secret_name}" from AWS Secrets Manager: {e}')
        if 'SecretString' in response:
            secret_value = response['SecretString']
        else:
            secret_value = base64.b64decode(response['SecretBinary'])
        return json.loads(secret_value)