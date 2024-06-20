from app import app, db
from app.models import Entry
from sqlalchemy import text

# Uygulama bağlamını aç
with app.app_context():
    # Veritabanı bağlantısını al
    engine = db.engine

    # Yeni sütunu ekle
    with engine.connect() as conn:
        conn.execute(text('ALTER TABLE entry ADD COLUMN sequence INTEGER;'))

    # Mevcut entry'lere sıra numarası atamak için kod
    entries = Entry.query.order_by(Entry.timestamp).all()
    for i, entry in enumerate(entries, start=1):
        entry.sequence = i
        db.session.commit()
