from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

# --- New: XP Mapping for Difficulty ---
XP_MAPPING = {
    'Easy': 10,
    'Medium': 25,
    'Hard': 50
}

# --- Rank Logic Function ---
def get_karmic_rank(xp):
    """Determines the user's Karmic Rank based on their experience points."""
    if xp >= 500:
        return 'Karmic Master'
    elif xp >= 200:
        return 'Community Elder'
    elif xp >= 50:
        return 'Active Peer'
    elif xp >= 10:
        return 'Helper Recruit'
    else:
        return 'Newbie'

# --- App Setup ---
app = Flask(__name__)
# CRITICAL FIX: Using a new database name to force a clean start with the correct schema
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///karmic_v2.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'karmic_mvp_secure_session_key' 

db = SQLAlchemy(app)

# --- Database Models ---

# Represents a user (Requester/Helper)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False) 
    coins = db.Column(db.Integer, default=100)
    experience_points = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<User {self.username} | Coins: {self.coins}>'

# Represents a request for help (the core transaction)
class Request(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    reward_coins = db.Column(db.Integer, nullable=False)
    difficulty = db.Column(db.String(20), default='Medium')
    xp_value = db.Column(db.Integer, default=25) 
    
    requester_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    helper_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True) 
    
    status = db.Column(db.String(30), default='Live') 
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # NEW: Relationship to messages for this specific request
    messages = db.relationship('Message', backref='request', lazy='dynamic') 

# NEW: Model for Chat Messages
class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('request.id'), nullable=False) # Links to the specific task chat
    sender_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    # Allows us to easily fetch the sender's username
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')

# Function to get the current logged-in user from the session
def get_current_user():
    """Retrieves the current logged-in user object."""
    user_id = session.get('user_id')
    if user_id:
        return db.session.get(User, user_id)
    return None

# --- Application Initialization ---

def initialize_app():
    """Initializes the database and creates default users if needed."""
    try:
        with app.app_context():
            # Check for the NEW database file
            db_path = os.path.join(os.getcwd(), 'karmic_v2.db')
            
            # CRITICAL: Force deletion of the old database file if it exists, 
            # to guarantee a clean schema update whenever the app starts.
            if os.path.exists(db_path):
                os.remove(db_path)
                print("--- Old database file deleted to ensure fresh schema. ---")
                
            print("--- Creating new database tables... ---")
            db.create_all()
            
            # Create test users if they don't exist
            if User.query.count() < 2:
                # Hash a simple password for test users
                hashed_pass = generate_password_hash("password") 
                
                if not User.query.filter_by(username='RequesterA').first():
                    db.session.add(User(username='RequesterA', password_hash=hashed_pass, coins=500, experience_points=120))
                if not User.query.filter_by(username='HelperB').first():
                    db.session.add(User(username='HelperB', password_hash=hashed_pass, coins=100, experience_points=60))
                db.session.commit()
                print("--- Default Users (RequesterA, HelperB) Created. (Password: 'password') ---")

    except Exception as e:
        print(f"ERROR during initialization: {e}")
        
initialize_app()


# --- Routes (Endpoints) ---

# Main Dashboard Route
@app.route('/')
def index():
    current_user = get_current_user()
    if not current_user:
        return redirect(url_for('login_signup'))
    
    live_requests = Request.query.filter(
        Request.status=='Live', 
        Request.requester_id != current_user.id
    ).all()
    
    my_requests = Request.query.filter(
        (Request.requester_id == current_user.id) | (Request.helper_id == current_user.id)
    ).all()
    
    # --- Leaderboard Logic ---
    all_users = User.query.all()
    leaderboard = sorted(
        all_users, 
        key=lambda user: (user.experience_points, user.coins, user.username), 
        reverse=True
    )[:10]
    
    user_rank = get_karmic_rank(current_user.experience_points)
    
    return render_template('dashboard.html', 
                           user=current_user, 
                           requests=live_requests, 
                           my_requests=my_requests, 
                           user_rank=user_rank,
                           leaderboard=leaderboard,
                           XP_MAPPING=XP_MAPPING) 

# Create Request Route
@app.route('/create_request', methods=['GET', 'POST'])
def create_request():
    requester = get_current_user()
    if not requester:
        return redirect(url_for('login_signup'))

    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        difficulty = request.form.get('difficulty')
        
        # Calculate XP and Coins based on difficulty
        xp_reward = XP_MAPPING.get(difficulty, 10) 
        reward = xp_reward # Coins = XP
        
        if requester.coins < reward:
            flash(f"You don't have enough Coins to offer this reward! Need {reward} Coins.")
            return redirect(url_for('create_request'))
            
        new_request = Request(
            title=title, 
            description=description, 
            reward_coins=reward, 
            difficulty=difficulty,
            xp_value=xp_reward,
            requester_id=requester.id
        )
        
        # Deduct coins (place in escrow)
        requester.coins -= reward
        
        db.session.add(new_request)
        db.session.commit()
        
        flash(f'Request "{title}" posted successfully! {reward} Coins are in escrow.')
        return redirect(url_for('index'))
    
    return render_template('create_request.html', user=requester, difficulties=XP_MAPPING.keys(), XP_MAPPING=XP_MAPPING)

# Accept Task Route
@app.route('/accept_task/<int:request_id>')
def accept_task(request_id):
    karmic_request = db.session.get(Request, request_id)
    helper = get_current_user()
    
    if not karmic_request or karmic_request.status != 'Live':
        flash('This request is no longer available.')
        return redirect(url_for('index'))

    if karmic_request.requester_id == helper.id:
        flash("You cannot accept your own request!")
        return redirect(url_for('index'))

    karmic_request.helper_id = helper.id
    karmic_request.status = 'Accepted'
    db.session.commit()
    
    flash(f'You accepted the task: "{karmic_request.title}". Use the chat feature to coordinate!')
    return redirect(url_for('index'))

# ROUTE 1: Helper Confirms Completion
@app.route('/helper_confirm/<int:request_id>')
def helper_confirm(request_id):
    karmic_request = db.session.get(Request, request_id)
    helper = get_current_user()

    if not karmic_request or karmic_request.helper_id != helper.id or karmic_request.status != 'Accepted':
        flash("Error: This task is not assigned to you or is not ready for confirmation.")
        return redirect(url_for('index'))

    karmic_request.status = 'Confirmed_By_Helper'
    db.session.commit()

    flash(f"You confirmed completion. Awaiting approval from the Requester!")
    return redirect(url_for('index'))

# ROUTE 2: Requester Approves and Releases Funds (Final Transaction)
@app.route('/requester_approve/<int:request_id>')
def requester_approve(request_id):
    karmic_request = db.session.get(Request, request_id)
    requester = get_current_user()
    
    if not karmic_request or karmic_request.requester_id != requester.id or karmic_request.status != 'Confirmed_By_Helper':
        flash("Error: You are not the requester or the helper has not yet confirmed completion.")
        return redirect(url_for('index'))
        
    # --- Transaction Logic ---
    helper = db.session.get(User, karmic_request.helper_id)
    if helper:
        # Transfer reward (released from escrow)
        helper.coins += karmic_request.reward_coins
        helper.experience_points += karmic_request.xp_value # Use the stored XP value
        
        # Calculate new rank
        new_rank = get_karmic_rank(helper.experience_points)
    
    # Final Status Update
    karmic_request.status = 'Completed'
    db.session.commit()

    flash(f"Approval successful! {karmic_request.reward_coins} Coins and {karmic_request.xp_value} XP transferred to the Helper. Helper's new rank: {new_rank}")
    return redirect(url_for('index'))


# --- NEW CHAT ROUTES ---

@app.route('/chat/<int:request_id>', methods=['GET'])
def chat_view(request_id):
    current_user = get_current_user()
    karmic_request = db.session.get(Request, request_id)

    # Check if user is involved (Requester or Helper)
    if not karmic_request or (karmic_request.requester_id != current_user.id and karmic_request.helper_id != current_user.id):
        flash("You are not authorized to view this chat.")
        return redirect(url_for('index'))

    # Fetch all messages for this request, ordered by time
    messages = Message.query.filter_by(request_id=request_id).order_by(Message.timestamp).all()
    
    # Get partner's username for display
    if karmic_request.requester_id == current_user.id:
        partner_id = karmic_request.helper_id
    else:
        partner_id = karmic_request.requester_id
        
    partner = db.session.get(User, partner_id) if partner_id else None
    
    return render_template('chat.html', 
                           user=current_user, 
                           request=karmic_request, 
                           messages=messages, 
                           partner=partner)

@app.route('/send_message/<int:request_id>', methods=['POST'])
def send_message(request_id):
    current_user = get_current_user()
    karmic_request = db.session.get(Request, request_id)
    content = request.form.get('content')

    if not content or not karmic_request:
        flash("Cannot send empty message or task does not exist.")
        return redirect(url_for('chat_view', request_id=request_id))

    # Security check: User must be Requester or Helper
    if karmic_request.requester_id != current_user.id and karmic_request.helper_id != current_user.id:
        flash("You are not authorized to chat about this task.")
        return redirect(url_for('index'))

    new_message = Message(
        request_id=request_id,
        sender_id=current_user.id,
        content=content
    )
    db.session.add(new_message)
    db.session.commit()
    
    return redirect(url_for('chat_view', request_id=request_id))


# Logout functionality
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("You have been successfully logged out.")
    return redirect(url_for('login_signup')) 


# Login/Signup Route (Secure Access)
@app.route('/login_signup', methods=['GET', 'POST'])
def login_signup():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        action = request.form.get('action') # 'login' or 'register'

        if not username or not password:
             flash('Please enter both username and password.')
             return redirect(url_for('login_signup'))
             
        user = User.query.filter_by(username=username).first()

        if action == 'register':
            if user:
                flash(f'User "{username}" already exists. Please log in.')
                return redirect(url_for('login_signup'))
            
            # --- Registration Logic ---
            new_user = User(
                username=username,
                password_hash=generate_password_hash(password)
            )
            db.session.add(new_user)
            db.session.commit()
            session['user_id'] = new_user.id
            flash(f'Registration successful! Welcome, {new_user.username}. You start with {new_user.coins} Coins!')
        
        elif action == 'login':
            if user and check_password_hash(user.password_hash, password):
                # --- Login Success Logic ---
                session['user_id'] = user.id
                flash(f'Welcome back, {user.username}!')
            else:
                flash('Invalid username or password.')
                return redirect(url_for('login_signup'))
        
        return redirect(url_for('index'))
            
    return render_template('login_signup.html')


# Main execution block
if __name__ == '__main__':
    try:
        app.run(debug=True)
    except Exception as e:
        print(f"--- FATAL SERVER ERROR ---")
        print(f"Error: {e}")
