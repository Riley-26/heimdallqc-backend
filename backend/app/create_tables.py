from app.db.database import Base, engine
from app.models.submission import Submission
# Import any other models you have here

def create_tables():
    # This will create all tables that don't exist yet
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully!")

if __name__ == "__main__":
    create_tables()