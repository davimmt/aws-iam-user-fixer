import boto3
from iam_user_keys import *
import datetime

BOOL_DEACTIVATE_CONSOLE_ACCESS = 0
BOOL_DEACTIVATE_KEY = 0
BOOL_DELETE_KEY = 0

DAYS_TO_DEACTIVATE_CONSOLE_ACCESS = 0
DAYS_TO_DEACTIVATE_KEY = 90
DAYS_TO_DELETE_KEY = 180

PRINT_PADDING = 18

iam = boto3.client('iam')
iam_ = boto3.resource('iam')
TODAY = datetime.datetime.now(datetime.timezone.utc).date()

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
            print('[CONSOLE] [DELETE]'.ljust(PRINT_PADDING), user.user_name, 'is', diff, 'days idle')
            if BOOL_DEACTIVATE_CONSOLE_ACCESS: iam.delete_login_profile(UserName=user.user_name)

    # Programatic access
    for key in iam.list_access_keys(UserName=user.user_name)['AccessKeyMetadata']:
        key_id = key['AccessKeyId']
        key_create_date = key['CreateDate'].date()
        key_last_use = get_last_use(key_id)['AccessKeyLastUsed']

        # Check if key was ever used
        try: diff = (TODAY - key_last_use['LastUsedDate'].date()).days
        except: diff = (TODAY - key_create_date).days
        
        if diff >= DAYS_TO_DELETE_KEY:
            print('[KEY]     [DELETE]'.ljust(PRINT_PADDING), key_id, 'is', diff, 'days idle')
            if BOOL_DELETE_KEY: delete_key(key.user_name, key_id)
        elif diff >= DAYS_TO_DEACTIVATE_KEY and diff < DAYS_TO_DELETE_KEY:
            print('[KEY] [DEACTIVATE]'.ljust(PRINT_PADDING), key_id, 'is', diff, 'days idle')
            if BOOL_DEACTIVATE_KEY: update_key(key.user_name, key_id, False)
