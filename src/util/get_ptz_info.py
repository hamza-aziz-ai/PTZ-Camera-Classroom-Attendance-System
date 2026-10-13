import os
import sys

from dotenv import load_dotenv
from onvif import ONVIFCamera

load_dotenv("secrets.env")

def main():
    # Usage: python get_ptz_info.py <camera_ip>; port and credentials come from secrets.env / environment
    ip = sys.argv[1]
    port = int(os.environ.get("CAM_PORT", 80))
    user = os.environ["CAM_USERNAME"]
    password = os.environ["CAM_PASSWORD"]

    # Create an ONVIFCamera instance
    camera = ONVIFCamera(ip, port, user, password)

    # Create the media service to interact with profiles
    media_service = camera.create_media_service()

    # Retrieve all available profiles from the camera
    profiles = media_service.GetProfiles()

    # Iterate over profiles to identify those that support PTZ
    ptz_profiles = []
    for profile in profiles:
        # Check if the profile has a PTZConfiguration attribute
        if hasattr(profile, 'PTZConfiguration') and profile.PTZConfiguration is not None:
            ptz_profiles.append(profile)
            print(f"Profile Token: {profile.token} supports PTZ.")

    # Optionally, query the PTZ service for additional details for each PTZ-enabled profile
    if ptz_profiles:
        ptz_service = camera.create_ptz_service()
        for profile in ptz_profiles:
            ptz_config_token = profile.PTZConfiguration.token
            try:
                # Pass the parameter using the correct name 'PTZConfigurationToken'
                detailed_config = ptz_service.GetConfiguration(ptz_config_token)
                print(f"Detailed PTZ Configuration for profile {profile.token}: {detailed_config}")
            except Exception as e:
                print(f"Failed to get PTZ configuration for profile {profile.token}: {e}")
    else:
        print("No PTZ-enabled profiles found.")

if __name__ == "__main__":
    main()
