import streamlit as st
import pandas as pd
import requests
import base64
import io
import plotly.express as px

# Access the GitHub token
GITHUB_TOKEN = st.secrets["github_token"]
REPO = 'angelicacalso/SummerFitnessChallenge'
FILE_PATH = 'user_data.xlsx'

# Function to get the Excel file content
def get_file_content():
    url = f'https://api.github.com/repos/{REPO}/contents/{FILE_PATH}'
    headers = {'Authorization': f'token {GITHUB_TOKEN}'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        file_content = response.json()['content']
        sha = response.json()['sha']  # Get the SHA of the existing file
        return pd.read_excel(io.BytesIO(base64.b64decode(file_content))), sha
    else:
        st.error("Error fetching file from GitHub.")
        return None, None

# Function to update the Excel file on GitHub
def update_file_on_github(new_data):
    existing_data, sha = get_file_content()
    if existing_data is not None:
        # Calculate the total score for the new entry
        new_data['Total Score'] = (new_data['Steps'] * 0.2) + (new_data['Pages Read'] * 30)
        
        # Concatenate existing data with new data
        updated_data = pd.concat([existing_data, new_data], ignore_index=True)
        
        # Calculate total score for all entries
        updated_data['Total Score'] = (updated_data['Steps'] * 0.2) + (updated_data['Pages Read'] * 30)

        # Ensure the Total Score column is numeric
        updated_data['Total Score'] = pd.to_numeric(updated_data['Total Score'], errors='coerce')

        # Use BytesIO to save the updated Excel file
        updated_excel = io.BytesIO()
        updated_data.to_excel(updated_excel, index=False)
        updated_excel.seek(0)  # Move to the beginning of the BytesIO object

        url = f'https://api.github.com/repos/{REPO}/contents/{FILE_PATH}'
        headers = {'Authorization': f'token {GITHUB_TOKEN}'}
        response = requests.put(url, headers=headers, json={
            'message': 'Update user data',
            'content': base64.b64encode(updated_excel.read()).decode(),
            'sha': sha  # Use the SHA of the existing file
        })

        if response.status_code == 200:
            return True  # Indicate success
        else:
            st.error("Error updating file on GitHub.")
            return False  # Indicate failure
    return False  # Indicate failure if existing data is None

# Function to reset state variables
def reset_state():
    st.session_state.username = ""
    st.session_state.steps = None
    st.session_state.pages_read = None
    st.session_state.confirm_submission = False

# Streamlit app title
st.title("Summer Fitness Challenge")

# Section 1 - Update user data
st.subheader("Update User Data")

# Initialize session state variables if they don't exist
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'steps' not in st.session_state:
    st.session_state.steps = None  # Set to None for empty input
if 'pages_read' not in st.session_state:
    st.session_state.pages_read = None  # Set to None for empty input
if 'confirm_submission' not in st.session_state:
    st.session_state.confirm_submission = False  # Initialize checkbox state

# Create input fields
st.session_state.username = st.text_input("Username", value=st.session_state.username)
st.session_state.steps = st.number_input("Number of Steps", min_value=0, value=st.session_state.steps if st.session_state.steps is not None else None)
st.session_state.pages_read = st.number_input("Number of Pages Read", min_value=0, value=st.session_state.pages_read if st.session_state.pages_read is not None else None)

# Enable checkbox only if all inputs are complete
confirm_submission = st.checkbox("I confirm that the above information is correct.", 
                                  value=st.session_state.confirm_submission, # if st.session_state.confirm_submission is not False else False,
                                  disabled=not (st.session_state.username and st.session_state.steps is not None and st.session_state.pages_read is not None))

# Create a submit button
if st.button("Submit"):
    # Check if all required fields are populated
    if st.session_state.username == "":
        st.warning("Please enter your Username.")
    elif st.session_state.steps is None:
        st.warning("Please enter the number of Steps (0 or more).")
    elif st.session_state.pages_read is None:
        st.warning("Please enter the number of Pages Read (0 or more).")
    elif not confirm_submission:
        st.warning("Please confirm that the information is correct before submitting (checkbox above the 'Submit' button).")
    else:
        # All fields are filled and checkbox is checked
        new_entry = pd.DataFrame([[st.session_state.username, st.session_state.steps, st.session_state.pages_read]], 
                                  columns=['Username', 'Steps', 'Pages Read'])
        
        # Attempt to update the Excel file on GitHub
        success = update_file_on_github(new_entry)
        
        if success:
            # Set success message in session state
            st.session_state.success_message = "Data successfully submitted! You may use the 'Retrieve Data' function at the bottom of this page to check."
            # Reset state variables after successful submission
            reset_state()
            # Rerun the app to reflect the cleared state
            st.rerun()
        else:
            st.error("Error fetching from the database.")
else:
    # Check if all required fields are populated and checkbox is checked
    if st.session_state.username and st.session_state.steps is not None and st.session_state.pages_read is not None and confirm_submission:
        st.warning("Please click the 'Submit' button.")

# Display success message if it exists
if 'success_message' in st.session_state:
    st.success(st.session_state.success_message)
    del st.session_state.success_message  # Clear the message after displaying it

# Section 2 - Leaderboard
st.subheader("Leaderboard")

data, _ = get_file_content()
if data is not None:
    # Convert usernames to lowercase for case-insensitive comparison
    data['Username'] = data['Username'].str.lower()
    
    # Calculate total score for all entries
    data['Total Score'] = (data['Steps'] * 0.2) + (data['Pages Read'] * 30)

    # Ensure the Total Score column is numeric
    data['Total Score'] = pd.to_numeric(data['Total Score'], errors='coerce')

    # Get top 10 participants and sort by Total Score in descending order
    top_10 = data.nlargest(10, 'Total Score')

    # Create a horizontal bar chart using Plotly
    fig = px.bar(top_10.sort_values(by='Total Score', ascending=True),  # Sort ascending for longest bar to appear on top
                  y='Username', 
                  x='Total Score', 
                  title='Top 10 Participants',
                  labels={'y': 'Participants', 'x': 'Total Score'},
                  orientation='h',
                  hover_data=['Steps', 'Pages Read'],
                  color_discrete_sequence=['#188CE5'])
    
    # Display the Plotly chart
    st.plotly_chart(fig)
else:
    st.error("No data available to display.")

# Section 3 - Retrieve data based on username
st.subheader("Retrieve User Data")
retrieve_username = st.text_input("Enter Username and click 'Retrieve Data'").lower()  # Convert input to lowercase
if st.button("Retrieve Data", key="retrieve_data_button"):
    if retrieve_username:
        user_data = data[data['Username'] == retrieve_username]  # Compare with lowercase usernames
        if not user_data.empty:
            st.write(user_data[['Steps', 'Pages Read', 'Total Score']])
        else:
            st.error("No data found for this username.")
    else:
        st.error("Please enter your Username.")
