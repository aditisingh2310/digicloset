from backend.app.db import engine
from backend.app import models

def create_all():
    models.Base.metadata.create_all(bind=engine)

if __name__ == '__main__':
    create_all()
    print("Created tables")
