import requests
import json

# Base URL for your API
BASE_URL = "http://localhost:8000"

# ---------- OWNER TESTING ----------

def test_create_owner():
    """Test creating a new owner"""
    url = f"{BASE_URL}/api/owners"
    data = {
        "email": "test@example.com",
        "name": "Test User",
        "domain": "localhost",
        "password": "testpassword123"
    }
    
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.text}")
        return None
    
def test_get_owner(owner_id):
    """Test fetching owner"""
    url = f"{BASE_URL}/api/owners/{owner_id}"
    
    response = requests.get(url)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.text}")
        return None
    

# ---------- API KEY TESTING ----------

def test_create_api_key(owner_id):
    """Test creating an API key for an owner"""
    url = f"{BASE_URL}/api/owners/{owner_id}/api-keys"
    data = {
        "name": "Test API Key"
    }
    
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.text}")
        return None
    
def test_get_api_keys(owner_id):
    """Test getting API keys for an owner"""
    url = f"{BASE_URL}/api/owners/{owner_id}/api-keys"
    
    response = requests.get(url)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.text}")
        return None
    
    
# ---------- SUBMISSION TESTING ----------
    
def test_create_submission(api_key):
    """Test creating a new submission"""
    url = f"{BASE_URL}/api/submissions"
    data = {
        "text": "hello, this is a test",
        "api_key": api_key,
        "custom_id": 20,
        "source_url": "http://localhost:3000"
    }
    
    response = requests.post(url, json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.text}")
        return None
    
def test_get_submissions(owner_id, submission_id = None):
    """Test getting a new submission"""
    url = f"{BASE_URL}/api/owners/{owner_id}/submissions/{submission_id if submission_id else ''}"
    
    response = requests.get(url)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error: {response.text}")
        return None
    
    
if __name__ == "__main__":
    #test_create_owner()
    
    #test_get_owner(1)
    
    #test_create_api_key(1)
    
    #test_get_api_keys(1)
    
    #test_create_submission("1gRXpe1ARPzRHzCnoZGYGJznt3SHDYe1as3My2FBRdWe7kQY")
    
    test_get_submissions(1, 4)