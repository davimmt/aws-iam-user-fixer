import boto3
from iam_user_keys import *
import datetime
import os

BOOL_DEACTIVATE_CONSOLE_ACCESS = int(os.environ['BOOL_DEACTIVATE_CONSOLE_ACCESS'])
BOOL_DEACTIVATE_KEY = int(os.environ['BOOL_DEACTIVATE_KEY'])
BOOL_DELETE_KEY = int(os.environ['BOOL_DELETE_KEY'])

DAYS_TO_DEACTIVATE_CONSOLE_ACCESS = int(os.environ['DAYS_TO_DEACTIVATE_CONSOLE_ACCESS'])
DAYS_TO_DEACTIVATE_KEY = int(os.environ['DAYS_TO_DEACTIVATE_KEY'])
DAYS_TO_DELETE_KEY = int(os.environ['DAYS_TO_DELETE_KEY'])

# Separete users and access keys by comma (,)
IGNORE_USERS = tuple(os.environ['IGNORE_USERS'].split(','))
IGNORE_KEYS = tuple(os.environ['IGNORE_KEYS'].split(','))

print(IGNORE_USERS)
exit()

OUTPUT_BUCKET_NAME = os.environ['OUTPUT_BUCKET_NAME']

PRINT_PADDING = 18

def lambda_handler(event, context):
    TODAY = datetime.datetime.now(datetime.timezone.utc).date()
    output_file = f"{TODAY}-iam-user-fixer-output.txt"
    output_file_path = "/tmp/" + output_file
    s3_path = f"{TODAY.year}/{TODAY.month}/" + output_file
    
    iam = boto3.client('iam')
    iam_ = boto3.resource('iam')
    
    with open(output_file_path, 'w+') as file:
        file.write('============\n')
        file.write(f"BOOL_DEACTIVATE_CONSOLE_ACCESS: {BOOL_DEACTIVATE_CONSOLE_ACCESS}\n")
        file.write(f"BOOL_DEACTIVATE_KEY: {BOOL_DEACTIVATE_KEY}\n")
        file.write(f"BOOL_DELETE_KEY: {BOOL_DELETE_KEY}\n")
        file.write(f"DAYS_TO_DEACTIVATE_CONSOLE_ACCESS: {DAYS_TO_DEACTIVATE_CONSOLE_ACCESS}\n")
        file.write(f"DAYS_TO_DEACTIVATE_KEY: {DAYS_TO_DEACTIVATE_KEY}\n")
        file.write(f"DAYS_TO_DELETE_KEY: {DAYS_TO_DELETE_KEY}\n")
        file.write('------------\n')
        file.write(f"IGNORE_USERS: {IGNORE_USERS}\n")
        file.write(f"IGNORE_KEYS: {IGNORE_KEYS}\n")
        file.write('============\n\n')
        
        for user in iam_.users.all():
            # Check if user has console access
            console_access = True
            try: iam_.LoginProfile(user.user_name).create_date
            except: console_access = False
    
            if console_access:
                # If user ever logged in
                try: diff = (TODAY - user.password_last_used.date()).days
                # User have never logged in
                except: diff = 100000000
                
                if diff >= DAYS_TO_DEACTIVATE_CONSOLE_ACCESS:
                    file.write(f"{'[CONSOLE] [DELETE]'.ljust(PRINT_PADDING)} {user.user_name} is {diff} days idle\n")
                    if BOOL_DEACTIVATE_CONSOLE_ACCESS and user.user_name not in IGNORE_USERS: iam.delete_login_profile(UserName=user.user_name)
    
            # Programatic access
            for key in iam.list_access_keys(UserName=user.user_name)['AccessKeyMetadata']:
                # Continue to next key if current key is not active
                if key['Status'] != 'Active': continue

                key_id = key['AccessKeyId']
                key_create_date = key['CreateDate'].date()
                key_last_use = get_last_use(key_id)['AccessKeyLastUsed']
    
                # Check if key was ever used
                try: diff = (TODAY - key_last_use['LastUsedDate'].date()).days
                except: diff = (TODAY - key_create_date).days
                
                if diff >= DAYS_TO_DELETE_KEY:
                    file.write(f"{'[KEY]     [DELETE]'.ljust(PRINT_PADDING)} {key_id} is {diff} days idle\n")
                    if BOOL_DELETE_KEY and key_id not in IGNORE_KEYS: delete_key(user.user_name, key_id)
                elif diff >= DAYS_TO_DEACTIVATE_KEY and diff < DAYS_TO_DELETE_KEY:
                    file.write(f"{'[KEY] [DEACTIVATE]'.ljust(PRINT_PADDING)} {key_id} is {diff} days idle\n")
                    if BOOL_DEACTIVATE_KEY and key_id not in IGNORE_KEYS: update_key(user.user_name, key_id, False)
    
    boto3.resource('s3').meta.client.upload_file(output_file_path, OUTPUT_BUCKET_NAME, s3_path)
