from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_user, current_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from app import app, db, login_manager
from app.models import User, Post, Entry, UserLike, UserDislike

owner_users = ['catoglu', 'catoglu123']
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def home():
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_entries = Entry.query.filter(Entry.timestamp >= one_hour_ago).order_by(Entry.timestamp.desc()).limit(10).all()

    posts = Post.query.all()
    for post in posts:
        if len(post.entries) == 0:
            db.session.delete(post)
    db.session.commit()
    return render_template('home.html', posts=posts, recent_entries=recent_entries)

@app.route('/poop_baslik')
def poop_baslik():
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_posts = db.session.query(Post, db.func.count(Entry.id).label('entry_count')) \
        .join(Entry) \
        .filter(Entry.timestamp >= one_hour_ago) \
        .group_by(Post.id) \
        .order_by(db.func.count(Entry.id).desc()) \
        .limit(10) \
        .all()

    return render_template('poop_baslik.html', recent_posts=recent_posts)

@app.route('/post/<int:post_id>', methods=['GET', 'POST'])
def post(post_id):
    post = Post.query.get_or_404(post_id)
    entries = Entry.query.filter_by(post_id=post.id).order_by(Entry.timestamp.desc()).all()
    top_entries = sorted(entries, key=lambda x: x.likes - x.dislikes, reverse=True)[:10]

    if request.method == 'POST':
        content = request.form['content']
        if content.strip() == "":
            flash('Boş entry girişi yapılamaz.', 'danger')
            return redirect(url_for('post', post_id=post_id))

        max_sequence = db.session.query(db.func.max(Entry.sequence)).scalar() or 0
        new_entry = Entry(content=content, user_id=current_user.id, post_id=post.id, sequence=max_sequence + 1)
        db.session.add(new_entry)
        db.session.commit()
        return redirect(url_for('post', post_id=post_id))
    
    show_all = request.args.get('show_all')
    if show_all:
        return render_template('post.html', post=post, entries=entries, top_entries=None)

    return render_template('post.html', post=post, entries=top_entries, top_entries=top_entries)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        flash('Account created successfully!', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('home'))
        else:
            flash('Login failed. Check your email and password', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/new_post', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        existing_post = Post.query.filter_by(title=title).first()
        if existing_post:
            flash('Bu başlık zaten mevcut, yeni başlık oluşturulmadı.', 'warning')
            return redirect(url_for('home'))
        else:
            post = Post(title=title)
            db.session.add(post)
            db.session.commit()

            max_sequence = db.session.query(db.func.max(Entry.sequence)).scalar() or 0
            new_entry = Entry(content=content, user_id=current_user.id, post_id=post.id, sequence=max_sequence + 1)
            db.session.add(new_entry)
            db.session.commit()
            
            return redirect(url_for('post', post_id=post.id))
    return render_template('new_post.html')

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q')
    if query.startswith('#'):
        entry_id = int(query[1:])
        entry = Entry.query.get_or_404(entry_id)
        return redirect(url_for('post', post_id=entry.post_id))
    elif query.startswith('@'):
        username = query[1:]
        user = User.query.filter_by(username=username).first_or_404()
        entries = Entry.query.filter_by(user_id=user.id).all()
        return render_template('search.html', entries=entries, user=user)
    else:
        posts = Post.query.filter(Post.title.contains(query)).all()
        return render_template('search.html', posts=posts)

@app.route('/delete_post/<int:post_id>', methods=['POST'])
@login_required
def delete_post(post_id):
    if current_user.username not in owner_users:
        flash('Bu işlemi gerçekleştirme yetkiniz yok.', 'danger')
        return redirect(url_for('home'))
    post = Post.query.get_or_404(post_id)
    db.session.delete(post)
    db.session.commit()
    flash('Başlık başarıyla silindi.', 'success')
    return redirect(url_for('home'))

@app.route('/delete_entry/<int:entry_id>', methods=['POST'])
@login_required
def delete_entry(entry_id):
    if current_user.username not in owner_users:
        flash('Bu işlemi gerçekleştirme yetkiniz yok.', 'danger')
        return redirect(url_for('home'))
    entry = Entry.query.get_or_404(entry_id)
    db.session.delete(entry)
    db.session.commit()
    flash('Entry başarıyla silindi.', 'success')
    return redirect(url_for('post', post_id=entry.post_id))

@app.route('/user/<username>')
def user_profile(username):
    user = User.query.filter_by(username=username).first_or_404()
    return render_template('profile.html', user=user)

@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_user.email = request.form['email']
        current_user.about_me = request.form['about_me']
        current_user.age = request.form['age']
        current_user.motto = request.form['motto']
        
        try:
            db.session.commit()
            flash('Profil güncellendi!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Profil güncellenemedi: {e}', 'danger')
        
        return redirect(url_for('user_profile', username=current_user.username))
    return render_template('edit_profile.html', user=current_user)

@app.errorhandler(404)
def page_not_found(e):
    posts = Post.query.all()
    return render_template('404.html', posts=posts), 404

@app.errorhandler(500)
def internal_server_error(e):
    posts = Post.query.all()
    return render_template('500.html', posts=posts), 500

@app.route('/poop_entry')
def poop_entry():
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_entries = Entry.query.filter(Entry.timestamp >= one_hour_ago).order_by(Entry.timestamp.desc()).limit(10).all()
    return render_template('poop_entry.html', recent_entries=recent_entries)

@app.route('/like_entry/<int:entry_id>', methods=['POST'])
@login_required
def like_entry(entry_id):
    entry = Entry.query.get_or_404(entry_id)
    if any(like.user_id == current_user.id for like in entry.user_likes):
        flash('You have already liked this entry.', 'danger')
        return redirect(url_for('post', post_id=entry.post_id))

    if any(dislike.user_id == current_user.id for dislike in entry.user_dislikes):
        entry.dislikes -= 1
        UserDislike.query.filter_by(user_id=current_user.id, entry_id=entry_id).delete()

    entry.likes += 1
    new_like = UserLike(user_id=current_user.id, entry_id=entry_id)
    db.session.add(new_like)
    db.session.commit()
    return redirect(url_for('post', post_id=entry.post_id))

@app.route('/dislike_entry/<int:entry_id>', methods=['POST'])
@login_required
def dislike_entry(entry_id):
    entry = Entry.query.get_or_404(entry_id)
    if any(dislike.user_id == current_user.id for dislike in entry.user_dislikes):
        flash('You have already disliked this entry.', 'danger')
     