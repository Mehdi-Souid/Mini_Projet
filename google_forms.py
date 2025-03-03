from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import json
import logging
from datetime import datetime
from dotenv import load_dotenv
import streamlit as st

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Define API scopes - simplified to only what's needed
SCOPES = ['https://www.googleapis.com/auth/forms']

def get_google_credentials():
    """Get and manage Google OAuth2 credentials"""
    creds = None

    # Check if we have valid stored credentials
    if os.path.exists('instance/token.json'):
        try:
            creds = Credentials.from_authorized_user_file('instance/token.json', SCOPES)
            if creds and not creds.expired:
                return creds
            elif creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                return creds
        except Exception as e:
            logger.error(f"Error loading stored credentials: {str(e)}")
            if os.path.exists('instance/token.json'):
                os.remove('instance/token.json')

    # Use manual OAuth flow configuration
    client_config = {
        "installed": {
            "client_id": "702452304478-b4cjuea923mlrp8fatk1tpkfe9rblb2k.apps.googleusercontent.com",
            "client_secret": "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",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob"]  # Use manual code entry
        }
    }

    try:
        # Create flow with manual code configuration
        flow = InstalledAppFlow.from_client_config(
            client_config,
            SCOPES
        )

        # Get authorization URL for manual flow
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )

        # Display instructions in Streamlit
        st.markdown("### Google Forms Authorization Required")
        st.markdown("""
        Please follow these steps to authorize the application:
        1. Click the link below to open Google's authorization page
        2. Sign in with your Google account
        3. Grant the requested permissions
        4. You will receive a code - copy it
        5. Paste the code in the text box below
        """)
        st.markdown(f"[Click here to authorize]({auth_url})")

        auth_code = st.text_input("Enter the authorization code:", key="auth_code")

        if auth_code:
            try:
                # Exchange the authorization code for credentials
                flow.fetch_token(code=auth_code)
                creds = flow.credentials

                # Save the credentials
                if not os.path.exists('instance'):
                    os.makedirs('instance')

                with open('instance/token.json', 'w') as token:
                    token.write(creds.to_json())

                return creds
            except Exception as e:
                st.error(f"Invalid authorization code: {str(e)}")
                logger.error(f"Authorization error: {str(e)}")
                return None

    except Exception as e:
        logger.error(f"Error setting up Google credentials: {str(e)}")
        st.error(f"Failed to set up authorization: {str(e)}")
        return None

    return None

def create_student_form(title="PFE Student Information Form"):
    """Create a new Google Form for student submissions"""
    try:
        # Get fresh credentials
        creds = get_google_credentials()
        if not creds:
            return {
                "success": False,
                "message": "Failed to obtain Google credentials. Please complete the authorization process."
            }

        # Build the Forms API service
        service = build(
            'forms',
            'v1',
            credentials=creds,
            cache_discovery=False
        )

        # Create form with basic info
        form = {
            "info": {
                "title": title,
                "documentTitle": title,
                "description": "Please fill out your PFE project information"
            }
        }

        # Create the form
        result = service.forms().create(body=form).execute()
        form_id = result.get('formId')

        if not form_id:
            raise ValueError("Failed to get form ID from creation response")

        logger.info(f"Created form with ID: {form_id}")

        # Define form questions
        questions = [
            {
                "createItem": {
                    "item": {
                        "title": "Full Name",
                        "description": "Enter your full name as it appears in official documents",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "textQuestion": {
                                    "type": "SHORT_ANSWER"
                                }
                            }
                        }
                    },
                    "location": {"index": 0}
                }
            },
            {
                "createItem": {
                    "item": {
                        "title": "Email Address",
                        "description": "Enter your academic email address",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "textQuestion": {
                                    "type": "SHORT_ANSWER"
                                }
                            }
                        }
                    },
                    "location": {"index": 1}
                }
            },
            {
                "createItem": {
                    "item": {
                        "title": "Project Title",
                        "description": "Enter the title of your PFE project",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "textQuestion": {
                                    "type": "PARAGRAPH"
                                }
                            }
                        }
                    },
                    "location": {"index": 2}
                }
            },
            {
                "createItem": {
                    "item": {
                        "title": "Supervisor",
                        "description": "Enter the name of your project supervisor",
                        "questionItem": {
                            "question": {
                                "required": True,
                                "textQuestion": {
                                    "type": "SHORT_ANSWER"
                                }
                            }
                        }
                    },
                    "location": {"index": 3}
                }
            }
        ]

        # Update form with questions
        update = {
            "requests": questions
        }

        service.forms().batchUpdate(
            formId=form_id,
            body=update
        ).execute()

        logger.info("Successfully added questions to form")

        return {
            "success": True,
            "formId": form_id,
            "formUrl": f"https://docs.google.com/forms/d/{form_id}/viewform",
            "message": "Form created successfully"
        }

    except HttpError as e:
        error_details = json.loads(e.content.decode('utf-8'))
        logger.error(f"Google API error: {json.dumps(error_details, indent=2)}")
        return {
            "success": False,
            "message": f"API error: {str(e)}",
            "details": error_details
        }

    except Exception as e:
        logger.error(f"Error creating form: {str(e)}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

if __name__ == "__main__":
    try:
        # Delete existing token to force new authentication
        if os.path.exists('instance/token.json'):
            os.remove('instance/token.json')
            logger.info("Deleted existing token file")

        result = create_student_form()
        if result["success"]:
            print(f"Form created successfully! URL: {result['formUrl']}")
        else:
            print(f"Error: {result['message']}")
    except Exception as e:
        print(f"Error: {str(e)}")