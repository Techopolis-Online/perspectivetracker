import os
import subprocess
from dotenv import load_dotenv

def set_heroku_config():
    """Set Heroku config variables from .env file"""
    # Load environment variables from .env file
    load_dotenv()
    
    # Get all environment variables
    env_vars = {
        'SECRET_KEY': os.getenv('SECRET_KEY'),
        'DEBUG': os.getenv('DEBUG'),
        'ALLOWED_HOSTS': os.getenv('ALLOWED_HOSTS'),
        'AUTH0_DOMAIN': os.getenv('AUTH0_DOMAIN'),
        'AUTH0_CLIENT_ID': os.getenv('AUTH0_CLIENT_ID'),
        'AUTH0_CLIENT_SECRET': os.getenv('AUTH0_CLIENT_SECRET'),
        'AUTH0_CALLBACK_URL': os.getenv('AUTH0_CALLBACK_URL'),
        'SOCIAL_AUTH_REDIRECT_IS_HTTPS': os.getenv('SOCIAL_AUTH_REDIRECT_IS_HTTPS'),
        'EMAIL_BACKEND': os.getenv('EMAIL_BACKEND'),
        'EMAIL_HOST': os.getenv('EMAIL_HOST'),
        'EMAIL_PORT': os.getenv('EMAIL_PORT'),
        'EMAIL_USE_SSL': os.getenv('EMAIL_USE_SSL'),
        'EMAIL_USE_TLS': os.getenv('EMAIL_USE_TLS'),
        'EMAIL_HOST_USER': os.getenv('EMAIL_HOST_USER'),
        'EMAIL_HOST_PASSWORD': os.getenv('EMAIL_HOST_PASSWORD'),
        'DEFAULT_FROM_EMAIL': os.getenv('DEFAULT_FROM_EMAIL'),
        'SERVER_EMAIL': os.getenv('SERVER_EMAIL'),
        'EMAIL_TIMEOUT': os.getenv('EMAIL_TIMEOUT'),
    }
    
    # Set each environment variable in Heroku
    for key, value in env_vars.items():
        if value:
            cmd = f'heroku config:set {key}="{value}"'
            print(f"Setting {key}...")
            subprocess.run(cmd, shell=True)

if __name__ == '__main__':
    set_heroku_config() 