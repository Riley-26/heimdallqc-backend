import requests
import json
from app.main import ai_analysis, plag_analysis, redact_text, ai_rewrite, auto_cite

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
    

# ---------- VERIFIED SITES TEST ----------

def test_get_verif_sites(domain):
    url = f"{BASE_URL}/api/verif-checker"
    
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
    
    #test_get_submissions(1, 4)
    
    #test_get_verif_sites("localhost")
    
    text = "In making a trench, soil from the excavation is used to create raised parapets running both in front of and behind the trench. Within the trench are firing positions along a raised forward step called a fire step, and duckboards are placed on the often muddy bottom of the trench to provide secure footing."
    
    reworded = """
        When constructing a trench, the excavated soil is piled up to form raised parapets on both the front and rear sides of the trench. Inside the trench, firing positions are established along a raised forward ledge known as a fire step, while duckboards are laid on the frequently muddy floor to ensure firm footing.
    """
    
    sources = [
        {
            "score": 100,
            "canAccess": True,
            "totalNumberOfWords": 54,
            "plagiarismWords": 54,
            "identicalWordCounts": 54,
            "similarWordCounts": 0,
            "url": "https://www.britannica.com/topic/trench-warfare",
            "author": "unknown",
            "description": "Trench warfare is combat in which armies attack, counterattack, and defend from relatively permanent ...",
            "title": "Trench warfare | Definition, History, Images, & Facts | Britannica",
            "publishedDate": "unknown",
            "source": "britannica.com",
            "citation": False,
            "plagiarismFound": [
                {
                    "startIndex": 0,
                    "endIndex": 306,
                    "sequence": "in making a trench, soil from the excavation is used to create raised parapets running both in front of and behind the trench. within the trench are firing positions along a raised forward step called a fire step, and duckboards are placed on the often muddy bottom of the trench to provide secure footing."
                }
            ],
            "is_excluded": False,
            "similarWords": []
        },
        {
            "score": 100,
            "canAccess": True,
            "totalNumberOfWords": 54,
            "plagiarismWords": 54,
            "identicalWordCounts": 54,
            "similarWordCounts": 0,
            "url": "https://janae23worldhistory.weebly.com/world-war-one.html",
            "author": "unknown",
            "description": "The worlds first global conflict, the Great War pitted the Central Powers of Germany, Austria-Hun ...",
            "title": "World War One ",
            "publishedDate": "unknown",
            "source": "janae23worldhistory.weebly.com",
            "citation": False,
            "plagiarismFound": [
                {
                    "startIndex": 0,
                    "endIndex": 306,
                    "sequence": "in making a trench, soil from the excavation is used to create raised parapets running both in front of and behind the trench. within the trench are firing positions along a raised forward step called a fire step, and duckboards are placed on the often muddy bottom of the trench to provide secure footing."
                }
            ],
            "is_excluded": False,
            "similarWords": []
        },
        {
            "score": 100,
            "canAccess": True,
            "totalNumberOfWords": 54,
            "plagiarismWords": 54,
            "identicalWordCounts": 54,
            "similarWordCounts": 0,
            "url": "https://americanconflict.weebly.com/world-war-i.html",
            "author": "unknown",
            "description": "When was World War I? World War 1 began on July 28, 1914 and lasted until November 11, 1918. The cau ...",
            "title": "World War I",
            "publishedDate": "unknown",
            "source": "americanconflict.weebly.com",
            "citation": False,
            "plagiarismFound": [
                {
                    "startIndex": 0,
                    "endIndex": 306,
                    "sequence": "in making a trench, soil from the excavation is used to create raised parapets running both in front of and behind the trench. within the trench are firing positions along a raised forward step called a fire step, and duckboards are placed on the often muddy bottom of the trench to provide secure footing."
                }
            ],
            "is_excluded": False,
            "similarWords": []
        },
        {
            "score": 100,
            "canAccess": True,
            "totalNumberOfWords": 54,
            "plagiarismWords": 54,
            "identicalWordCounts": 54,
            "similarWordCounts": 0,
            "url": "https://tougheryeti6.wixsite.com/viva-la-france/world-war-1",
            "author": "unknown",
            "description": "What caused WW1?World War 1, also called the First World War, The Great War, or The War to end all W ...",
            "title": "World War 1 | Viva La France",
            "publishedDate": "unknown",
            "source": "tougheryeti6.wixsite.com",
            "citation": False,
            "plagiarismFound": [
                {
                    "startIndex": 0,
                    "endIndex": 306,
                    "sequence": "in making a trench, soil from the excavation is used to create raised parapets running both in front of and behind the trench. within the trench are firing positions along a raised forward step called a fire step, and duckboards are placed on the often muddy bottom of the trench to provide secure footing."
                }
            ],
            "is_excluded": False,
            "similarWords": []
        },
        {
            "score": 97,
            "canAccess": True,
            "totalNumberOfWords": 54,
            "plagiarismWords": 52,
            "identicalWordCounts": 52,
            "similarWordCounts": 0,
            "url": "https://slideplayer.com/slide/10096220/",
            "author": "Richard Connell",
            "description": "Presentation on theme: \"Friday, August 31, 2012 Objectives: I can identify and correct run- ons and  ...",
            "title": "Friday, August 31, 2012 Objectives: I can identify and correct run- ons and fragments. I can define vocabulary words for a short story. Key Terms: 1. Game. -  ppt download",
            "publishedDate": "unknown",
            "source": "slideplayer.com",
            "citation": False,
            "plagiarismFound": [
                {
                    "startIndex": 0,
                    "endIndex": 69,
                    "sequence": "in making a trench, soil from the excavation is used to create raised"
                },
                {
                    "startIndex": 79,
                    "endIndex": 297,
                    "sequence": "running both in front of and behind the trench. within the trench are firing positions along a raised forward step called a fire step, and duckboards are placed on the often muddy bottom of the trench to provide secure"
                }
            ],
            "is_excluded": False,
            "similarWords": []
        },
        {
            "score": 97,
            "canAccess": True,
            "totalNumberOfWords": 54,
            "plagiarismWords": 52,
            "identicalWordCounts": 52,
            "similarWordCounts": 0,
            "url": "https://www.slideserve.com/tommy/key-terms-1-game-2-yacht-3-cliffs-4-chateau-5-gargoyle-6-cossack-7-ennui-8-knouter",
            "author": "tommy",
            "description": "Friday, August 31, 2012 Objectives: I can identify and correct run-ons and fragments. I can define v ...",
            "title": "Key Terms : 1. Game 2. Yacht 3. cliffs 4. Chateau 5. Gargoyle 6. Cossack 7. Ennui 8. Knouter - SlideServe",
            "publishedDate": 1405814400000,
            "source": "slideserve.com",
            "citation": False,
            "plagiarismFound": [
                {
                    "startIndex": 0,
                    "endIndex": 69,
                    "sequence": "in making a trench, soil from the excavation is used to create raised"
                },
                {
                    "startIndex": 79,
                    "endIndex": 297,
                    "sequence": "running both in front of and behind the trench. within the trench are firing positions along a raised forward step called a fire step, and duckboards are placed on the often muddy bottom of the trench to provide secure"
                }
            ],
            "is_excluded": False,
            "similarWords": []
        },
        {
            "score": 39,
            "canAccess": True,
            "totalNumberOfWords": 54,
            "plagiarismWords": 21,
            "identicalWordCounts": 21,
            "similarWordCounts": 0,
            "url": "https://www.britannica.com/topic/fire-step",
            "author": "unknown",
            "description": "Other articles where fire step is discussed: trench warfare: Early developments: raised forward ste ...",
            "title": "Fire step | warfare | Britannica",
            "publishedDate": 1747353600000,
            "source": "britannica.com",
            "citation": False,
            "plagiarismFound": [
                {
                    "startIndex": 181,
                    "endIndex": 297,
                    "sequence": "forward step called a fire step, and duckboards are placed on the often muddy bottom of the trench to provide secure"
                }
            ],
            "is_excluded": False,
            "similarWords": []
        },
        {
            "score": 0,
            "canAccess": False,
            "totalNumberOfWords": 54,
            "plagiarismWords": 0,
            "identicalWordCounts": 0,
            "similarWordCounts": 0,
            "url": "https://ludwig.guru/s/making+trenches?ref=related",
            "author": "unknown",
            "description": "unknown",
            "title": "making trenches | English examples in context - Ludwig.guru",
            "publishedDate": "unknown",
            "source": "unknown",
            "citation": False,
            "plagiarismFound": [],
            "is_excluded": False,
            "similarWords": []
        },
        {
            "score": 0,
            "canAccess": False,
            "totalNumberOfWords": 54,
            "plagiarismWords": 0,
            "identicalWordCounts": 0,
            "similarWordCounts": 0,
            "url": "https://www.sfdr-cisd.org/media/0ddine4l/sfdrcisd-social-studies-6th-grade_b_v250_sew_s1.pdf",
            "author": "unknown",
            "description": "unknown",
            "title": "[PDF] SFDRCISD Social Studies 6th Grade",
            "publishedDate": "unknown",
            "source": "unknown",
            "citation": False,
            "plagiarismFound": [],
            "is_excluded": False,
            "similarWords": []
        },
        {
            "score": 0,
            "canAccess": False,
            "totalNumberOfWords": 54,
            "plagiarismWords": 0,
            "identicalWordCounts": 0,
            "similarWordCounts": 0,
            "url": "https://ludwig.guru/s/a+firing+step?ref=related",
            "author": "unknown",
            "description": "unknown",
            "title": "a firing step | English examples in context | Ludwig",
            "publishedDate": "unknown",
            "source": "unknown",
            "citation": False,
            "plagiarismFound": [],
            "is_excluded": False,
            "similarWords": []
        }
    ]
    
    #print(ai_analysis(reworded))
    #print(plag_analysis(text))
    print(redact_text(text, sources))
    #print(ai_rewrite(text))
    #print(auto_cite(text, sources))