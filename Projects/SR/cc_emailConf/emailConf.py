import requests
import time
import datetime
import tkinter as tk
from tkinter import filedialog
import csv
import io
import json


# global variables
client_id = "ace6be02-4bb3-470c-ab39-fb2983bd9010"
scope = "contact_data campaign_data offline_access account_read account_update"
auth_endpoint = "https://authz.constantcontact.com/oauth2/default/v1/device/authorize"
token_endpoint = "https://authz.constantcontact.com/oauth2/default/v1/token"
grant_type = "urn:ietf:params:oauth:grant-type:device_code"
from_name= "Alex"
from_email = "alexhutton99@gmail.com"
reply_to_email = "alexhutton99@gmail.com"
subject = "Race Day Confirmation"

"""*******************************************************************************
            The section below starts Device Flow
********************************************************************************"""

data = {
    "client_id": client_id,
    "scope": scope
}

response = requests.post(auth_endpoint, data=data)
print("Response content:", response.text)
response_data = response.json()

if response.status_code == 200:
    device_code = response_data["device_code"]
    user_code = response_data["user_code"]
    verification_uri = response_data["verification_uri_complete"]

    print("**********************************")
    print("Please visit:", verification_uri)
    print("Enter code:", user_code)
    print("**********************************")

    time.sleep(20)

    # Step 2: Poll for Token
while True:
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    token_data = {
        "client_id": client_id,
        "device_code": device_code,
        "grant_type": grant_type
    }

    token_response = requests.post(token_endpoint, headers=headers, data=token_data)
    # print("token response:", token_response.text)
    
    if token_response.status_code == 200:
        try:
            token_data = token_response.json()
        except requests.exceptions.JSONDecodeError as e:
            print("Error decoding JSON:", e)
            break

        if "access_token" in token_data:
            access_token = token_data["access_token"]
            # print("Access token:", access_token)
            break
    else:
        print("Token request failed with status code:", token_response.status_code)


# Create a new list with today's date
today_date = datetime.datetime.now().strftime("%Y-%m-%d")
new_list_name = f"conf_{today_date}"

list_endpoint = "https://api.cc.email/v3/contact_lists"
list_payload = {
    "name": new_list_name,
    "description": "A list of people signed up for an event in the last 24 hours"
}

list_headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

list_response = requests.post(list_endpoint, json=list_payload, headers=list_headers)
list_response_json = list_response.json() 

if list_response.status_code == 201:
    print(f"New list '{new_list_name}' created successfully!")
    print("List response JSON:", list_response_json)  # Print the JSON response for debugging
else:
    print("Error creating list:", list_response.status_code, list_response.text)
    
# Get the list_id of the newly created list
try:
    list_id = list_response_json["list_id"]
except KeyError:
    print("Error: 'list_id' not found in list response JSON")
    exit()  # Exit the script if 'id' is not found


# Open file dialog to select a .xls file (which is actually a .txt file)
root = tk.Tk()
root.withdraw()  # Hide the main window

xls_file_path = filedialog.askopenfilename(filetypes=[("XLS Files", "*.xls")])
if not xls_file_path:
    print("No .xls file selected. Exiting.")
    exit()

# Read the text file content
with open(xls_file_path, "r") as txt_file:
    txt_data = txt_file.read()

# Split the text data into lines
lines = txt_data.split('\n')

# Prepare the data for upload
csv_data = []
for line in lines:
    columns = line.split('\t')
    csv_data.append(columns)

# Convert the data to CSV format
csv_output = io.StringIO()
csv_writer = csv.writer(csv_output)
csv_writer.writerows(csv_data)
csv_contents = csv_output.getvalue()

upload_endpoint = f"https://api.cc.email/v3/activities/contacts_file_import"

list_ids = [list_id]  # Use the list_id of the newly created list

# Prepare the data for upload
upload_data = {
    "file": ("contacts.csv", csv_contents.encode('utf-8'), "text/csv"),
    "list_ids": (None, ",".join(list_ids))
}

upload_headers = {
    "Authorization": f"Bearer {access_token}"
}

upload_response = requests.post(upload_endpoint, files=upload_data, headers=upload_headers)
if upload_response.status_code == 201:
    print("Contacts uploaded successfully!")
else:
    print("Error uploading contacts:", upload_response.status_code, upload_response.text)

"""*********************************************************************************
            The section belo finds the campaign id 
**********************************************************************************"""

# Fetch the list of campaigns
campaigns_endpoint = "https://api.cc.email/v3/emails"
campaigns_response = requests.get(campaigns_endpoint, headers=upload_headers)
campaigns_response_json = campaigns_response.json()

# Find the campaign titled "dailyRaceConf"
target_campaign = None
for campaign in campaigns_response_json['campaigns']:
    if campaign['name'] == 'dailyRaceConf':
        target_campaign = campaign
        break

# Check if the campaign was found
if target_campaign is None:
    print("Campaign 'dailyRaceConf' not found.")
else: 
    print("campaign 'dialyRaceConf' found")

# Extract the campaign ID
campaign_id = target_campaign['campaign_id']

#print('campaign_id: ',campaign_id)

# Get campaign details
campaign_activity_endpoint = f"https://api.cc.email/v3/emails/{campaign_id}/"
campaign_activity_headers = {
    "Authorization": f"Bearer {access_token}"
}

campaign_activity_response = requests.get(campaign_activity_endpoint, headers=campaign_activity_headers)
print(campaign_activity_response.text)
campaign_activity_json = campaign_activity_response.json()
# Find the campaign activity ID for primary_email
primary_email_activity = next((activity for activity in campaign_activity_json["campaign_activities"] if activity["role"] == "primary_email"), None)
primary_email_activity_id = primary_email_activity["campaign_activity_id"] if primary_email_activity else None

# Print the primary_email campaign activity ID
if primary_email_activity_id:
    print("Primary Email Campaign Activity ID:", primary_email_activity_id)
else:
    print("Primary Email Campaign Activity ID not found.")
    # Print the campaign activity IDs
#for activity_id in campaign_activity_ids:
 #   print("Campaign Activity ID:", activity_id)
if campaign_activity_response.status_code == 200:
    campaign_name = campaign_activity_json.get("name", "Unknown Campaign")
    print(f"Details for Campaign '{campaign_name}':")
    print("Campaign Activity ID:", primary_email_activity_id )
else:
    print("Error getting campaign details:", campaign_activity_response.status_code, campaign_activity_response.text)

"""*******************************************************************************
                Update the contact list to the specified campaign
********************************************************************************"""

update_campaign_endpoint = f"https://api.cc.email/v3/emails/activities/{primary_email_activity_id}"

# Specify the contact list IDs you want to send the campaign to
contact_list_ids = [list_id]

# Prepare the updated data for the email campaign activity
updated_campaign_data = {
    "contact_list_ids": contact_list_ids,
    "from_name": from_name,
    "from_email": from_email,
    "reply_to_email": reply_to_email,
    "subject": subject,
    "current_status" : "Done",
    "role" : "primary_email",
}

# Make the PUT request to update the email campaign activity
update_campaign_headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

update_campaign_response = requests.put(update_campaign_endpoint, json=updated_campaign_data, headers=update_campaign_headers)

if update_campaign_response.status_code == 200:
    print("Email campaign activity updated successfully with contact list!")
else:
    print("Error updating email campaign activity:", update_campaign_response.status_code, update_campaign_response.text)
    exit

"""********************************************************************************
                         schedule the campaign for sending
********************************************************************************"""

# Calculate the scheduled date as one day from the current date
scheduled_date = (datetime.datetime.now() + datetime.timedelta(days=1)).replace(microsecond=0)
scheduled_date_iso = scheduled_date.isoformat() + ".000Z"  # Add milliseconds


# Send the campaign by scheduling it one day from now
schedule_campaign_endpoint = f"https://api.cc.email/v3/emails/activities/{primary_email_activity_id}/schedules"


schedule_campaign_data = {
    "scheduled_date": scheduled_date_iso
}

schedule_headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

schedule_campaign_response = requests.post(schedule_campaign_endpoint, json=schedule_campaign_data, headers=schedule_headers)

if schedule_campaign_response.status_code == 201:
    print("Campaign scheduled successfully!", schedule_campaign_response.text)
else:
    print("Error scheduling campaign:", schedule_campaign_response.status_code, schedule_campaign_response.text)

"""********************************************************************************
                      delete list from 1 day before
********************************************************************************"""

# Get yesterday's date
yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
formatted_date = yesterday.strftime("%Y-%m-%d")

# Construct the list name
list_name = f"conf_{formatted_date}"

# Construct the endpoint to retrieve contact lists
list_endpoint = f"https://api.cc.email/v3/contact_lists"

# Set headers for API request
headers = {
    "Authorization": f"Bearer {access_token}"
}

# Make a GET request to retrieve contact lists
response = requests.get(list_endpoint, headers=headers)

if response.status_code == 200:
    lists = response.json()["lists"]

    # Find the list with the constructed name
    target_list = None
    for lst in lists:
        if lst["name"] == list_name:
            target_list = lst
            break

    if target_list:
        # Delete the target list
        prev_day_list_id = target_list["list_id"]
        delete_endpoint = f"https://api.cc.email/v3/contact_lists/{prev_day_list_id}"
        delete_response = requests.delete(delete_endpoint, headers=headers)

        if delete_response.status_code == 202:
            print(f"Successfully deleted list '{list_name}'")
        else:
            print(f"Failed to delete list '{list_name}': {delete_response.text}")
    else:
        print(f"List '{list_name}' not found")
else:
    print(f"Failed to retrieve contact lists: {response.text}")