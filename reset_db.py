from app import app, db
from app.models import User
from werkzeug.security import generate_password_hash

with app.app_context():
    db.drop_all()
    db.create_all()

    # Example user with owner privileges
    owner_user = User(username='catoglu', email='mcatoglu@outlook.com', password=generate_password_hash('anan123', method='pbkdf2:sha256'))
    owner_user2 = User(username='catoglu123', email='mcatoglu@hotmail.com', password=generate_password_hash('anan123', method='pbkdf2:sha256'))
    
    db.session.add(owner_user)
    db.session.add(owner_user2)
    db.session.commit()
