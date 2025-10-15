import requests
import json

# Base URL for your API
BASE_URL = "http://127.0.0.1:8000"

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
    
def create_webhook():
    url = f"{BASE_URL}/api/v1/webhooks/create-webhook"
    data = {
        "name": "hello",
        "endpoint": "http://127.0.0.1:8000"
    }
    
    response = requests.post(url, json=data)
    
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
    
def test_datetime():
    from datetime import datetime, timezone
    now = datetime.now(tz=timezone.utc)
    print(now >= datetime.fromisoformat("2025-11-05T22:44:11.000Z"))


def test_type():
    url = f"{BASE_URL}/api/v1/get_type"
    
    response = requests.get(url)
    
    print(response.json())
    
if __name__ == "__main__":
    #test_create_owner()
    
    #test_get_owner(1)
    
    #test_create_api_key(1)
    
    #test_get_api_keys(1)
    
    #test_create_submission("1gRXpe1ARPzRHzCnoZGYGJznt3SHDYe1as3My2FBRdWe7kQY")
    
    #test_get_submissions(1, 4)
    
    #test_get_verif_sites("localhost")
    
    text = "When constructing a trench, the excavated soil is piled up to form raised parapets on both the front and rear sides of the trench. Inside the trench, firing positions are established along a raised forward ledge known as a fire step, while duckboards are laid on the frequently muddy floor to ensure firm footing. As early as the 19th century, criminal profiling began to emerge, with the Jack the Ripper case being the first instance of criminal profiling, by forensic doctor and surgeon Thomas Bond. In the first decade of the 20th century, Hugo Münsterberg, the first director of Harvard's psychological laboratory and a student of Wilhelm Wundt, one of the first experimental psychologists, authored On the Witness Stand. In the publication, Münsterberg attempted to demonstrate how psychological research could be applied in legal proceedings. Sigmund Freud also discussed how psychopathological processes play a role in criminal behavior. Other significant early figures in forensic psychology include Lightner Witmer, and William Healy.In 1917, the lie detector was invented by the psychologist William Marston. Six years after its invention, Marston brought his lie detector to court in the case of Frye v. United States at the request of James A. Frye's attorneys, who hoped Marston's device would prove their client's innocence."
    
    reworded = """
        As early as the 19th century, criminal profiling began to emerge, with the Jack the Ripper case being the first instance of criminal profiling, by forensic doctor and surgeon Thomas Bond. In the first decade of the 20th century, Hugo Münsterberg, the first director of Harvard's psychological laboratory and a student of Wilhelm Wundt, one of the first experimental psychologists, authored On the Witness Stand. In the publication, Münsterberg attempted to demonstrate how psychological research could be applied in legal proceedings. Sigmund Freud also discussed how psychopathological processes play a role in criminal behavior. Other significant early figures in forensic psychology include Lightner Witmer, and William Healy.
    """
    
    l_plag = """
        I think the grossest thing I've ever encountered were fruit flies in a refrigerator. And I don't mean like a couple fruit flies. I'm talking HUNDREDS of them layered in the bottom of the fridge, little piles of them in the corners of the shelves and clumps in the doors. This was a WORKING refrigerator mind you. How did they even get in there??? And how do you continue to use a fridge with dead bugs in it?
    """
    l_ai = """
        So I finally decided to deep clean my kitchen this weekend, and honestly, I'm kind of embarrassed by what I found. There were these weird sticky spots on the floor that I've apparently been stepping over for months without actually dealing with them. And don't even get me started on the back of the fridge - I pulled it out from the wall and there was this whole ecosystem back there. I'm talking dust, crumbs, and what might have been a petrified french fry from like two years ago.
        The worst part was definitely the oven, though. I've been using it regularly but somehow convinced myself that the self-cleaning function was enough. Turns out it's not. There was this layer of burnt-on grease that I had to scrape off with one of those metal spatula things, and it took forever. My arm was actually sore the next day. I went through an entire roll of paper towels and probably used way too much cleaning spray, but at least it's done now.
        The funny thing is, once I got started I couldn't stop. I ended up reorganizing all my cabinets too, throwing out spices that expired in 2019, and discovering I apparently own four cheese graters for some reason. I have no memory of buying four cheese graters. I live alone. Why would I need four? Anyway, my kitchen looks amazing now and I keep walking in there just to admire it. I'm sure this feeling will last about three days before everything gets messy again, but for now I'm going to enjoy it. Maybe I'll even cook something more ambitious than pasta for once.
    """
    l_mix_ai_plag = """
        So I finally decided to deep clean my kitchen this weekend, and honestly, I'm kind of embarrassed by what I found. There were these weird sticky spots on the floor that I've apparently been stepping over for months without actually dealing with them. And don't even get me started on the back of the fridge - I pulled it out from the wall and there was this whole ecosystem back there. I'm talking dust, crumbs, and what might have been a petrified french fry from like two years ago.
        The worst part was definitely the oven, though. I've been using it regularly but somehow convinced myself that the self-cleaning function was enough.
        I think the grossest thing I've ever encountered were fruit flies in a refrigerator. And I don't mean like a couple fruit flies. I'm talking HUNDREDS of them layered in the bottom of the fridge, little piles of them in the corners of the shelves and clumps in the doors. This was a WORKING refrigerator mind you. How did they even get in there??? And how do you continue to use a fridge with dead bugs in it?
    """
    l_mix_ai_human = """
        So I finally decided to deep clean my kitchen this weekend, and honestly, I'm kind of embarrassed by what I found. There were these weird sticky spots on the floor that I've apparently been stepping over for months without actually dealing with them. And don't even get me started on the back of the fridge - I pulled it out from the wall and there was this whole ecosystem back there. I'm talking dust, crumbs, and what might have been a petrified french fry from like two years ago.
        The worst part was definitely the oven, though. I've been using it regularly but somehow convinced myself that the self-cleaning function was enough.
        I've always hated cleaning, the kitchen is by far the worst room. I don't know why, something about me I guess. But if I really have to clean, I will. Tools like my vacuum make it so much easier though, and sometimes I can get some enjoyment out of it at least making it slightly less painful. I wonder, maybe I should get it professionally cleaned more often. It would save me so much time so that I can focus on other more important things.
    """
    l_mix_plag_human = """
        I think the grossest thing I've ever encountered were fruit flies in a refrigerator. And I don't mean like a couple fruit flies. I'm talking HUNDREDS of them layered in the bottom of the fridge, little piles of them in the corners of the shelves and clumps in the doors. This was a WORKING refrigerator mind you. How did they even get in there??? And how do you continue to use a fridge with dead bugs in it?
        I've always hated cleaning, the kitchen is by far the worst room. I don't know why, something about me I guess. But if I really have to clean, I will. Tools like my vacuum make it so much easier though, and sometimes I can get some enjoyment out of it at least making it slightly less painful. I wonder, maybe I should get it professionally cleaned more often. It would save me so much time so that I can focus on other more important things.
    """
    l_multi_plag = """
        I think the grossest thing I've ever encountered were fruit flies in a refrigerator. And I don't mean like a couple fruit flies. I'm talking HUNDREDS of them layered in the bottom of the fridge, little piles of them in the corners of the shelves and clumps in the doors. This was a WORKING refrigerator mind you. How did they even get in there??? And how do you continue to use a fridge with dead bugs in it?
        As early as the 19th century, criminal profiling began to emerge, with the Jack the Ripper case being the first instance of criminal profiling, by forensic doctor and surgeon Thomas Bond. In the first decade of the 20th century, Hugo Münsterberg, the first director of Harvard's psychological laboratory and a student of Wilhelm Wundt, one of the first experimental psychologists, authored On the Witness Stand. In the publication, Münsterberg attempted to demonstrate how psychological research could be applied in legal proceedings. Sigmund Freud also discussed how psychopathological processes play a role in criminal behavior. Other significant early figures in forensic psychology include Lightner Witmer, and William Healy.
    """
    l_multi_ai = """
        I've been thinking about getting a dog lately, but I'm honestly not sure if I'm ready for that kind of commitment. My apartment's pretty small, and I work long hours most days. Plus, I'd feel terrible leaving a puppy alone all the time. Maybe I should start with fostering first? That way I could see if it's actually doable before making a permanent decision. Or I could just get more houseplants instead.
        So I finally decided to deep clean my kitchen this weekend, and honestly, I'm kind of embarrassed by what I found. There were these weird sticky spots on the floor that I've apparently been stepping over for months without actually dealing with them. And don't even get me started on the back of the fridge - I pulled it out from the wall and there was this whole ecosystem back there. I'm talking dust, crumbs, and what might have been a petrified french fry from like two years ago.
    """
    
    s_plag = "First off, we have been using these cleaners for a few months. I'm immunocompromised and have them use our products, buckets, and supplies to prevent flare ups from certain chemicals. I also have a clutter free home and take generally about an hour to make sure we have all the supplies out for the cleaners and to make sure they have the easiest job ever. Literally moving stuff and making sure that they won't have to move anything. So, in my opinion, this is a pretty easy home to clean. It's mainly light cleaning. Everything is laid out and provided for them. They don't have to bring anything in but their abled bodies."
    s_ai = "I've been thinking about getting a dog lately, but I'm honestly not sure if I'm ready for that kind of commitment. My apartment's pretty small, and I work long hours most days. Plus, I'd feel terrible leaving a puppy alone all the time. Maybe I should start with fostering first? That way I could see if it's actually doable before making a permanent decision. Or I could just get more houseplants instead."
    s_mix_ai_plag = "I've been thinking about getting a dog lately, but I'm honestly not sure if I'm ready for that kind of commitment. My apartment's pretty small, and I work long hours most days. Plus, I'd feel terrible leaving a puppy alone all the time. I think the grossest thing I've ever encountered were fruit flies in a refrigerator. And I don't mean like a couple fruit flies. I'm talking HUNDREDS of them layered in the bottom of the fridge, little piles of them in the corners of the shelves and clumps in the doors."
    s_mix_ai_human = "I've been thinking about getting a dog lately, but I'm honestly not sure if I'm ready for that kind of commitment. My apartment's pretty small, and I work long hours most days. Plus, I'd feel terrible leaving a puppy alone all the time. I've always hated cleaning, the kitchen is by far the worst room. I don't know why, something about me I guess. But if I really have to clean, I will. Tools like my vacuum make it so much easier though, and sometimes I can get some enjoyment out of it at least making it slightly less painful. I wonder, maybe I should get it professionally cleaned more often. It would save me so much time so that I can focus on other more important things."
    s_mix_plag_human = "First off, we have been using these cleaners for a few months. I'm immunocompromised and have them use our products, buckets, and supplies to prevent flare ups from certain chemicals. I also have a clutter free home and take generally about an hour to make sure we have all the supplies out for the cleaners and to make sure they have the easiest job ever. I've always hated cleaning, the kitchen is by far the worst room. I don't know why, something about me I guess. But if I really have to clean, I will. Tools like my vacuum make it so much easier though, and sometimes I can get some enjoyment out of it at least making it slightly less painful. I wonder, maybe I should get it professionally cleaned more often. It would save me so much time so that I can focus on other more important things."
    s_multi_plag = "I think the grossest thing I've ever encountered were fruit flies in a refrigerator. And I don't mean like a couple fruit flies. I'm talking HUNDREDS of them layered in the bottom of the fridge, little piles of them in the corners of the shelves and clumps in the doors. First off, we have been using these cleaners for a few months. I'm immunocompromised and have them use our products, buckets, and supplies to prevent flare ups from certain chemicals. I also have a clutter free home and take generally about an hour to make sure we have all the supplies out for the cleaners."
    s_multi_ai = "I've been thinking about getting a dog lately, but I'm honestly not sure if I'm ready for that kind of commitment. My apartment's pretty small, and I work long hours most days. Plus, I'd feel terrible leaving a puppy alone all the time. So I finally decided to deep clean my kitchen this weekend, and honestly, I'm kind of embarrassed by what I found. There were these weird sticky spots on the floor that I've apparently been stepping over for months without actually dealing with them. And don't even get me started on the back of the fridge."
    
    
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
    #print(plag_analysis(l_multi_plag, ""))
    #print(redact_text(text, sources))
    #print(ai_rewrite(text, [[313,1337]]))
    #print(auto_cite(text, sources))
    #print(create_webhook())
    test_type()