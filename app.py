from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import datetime
import re
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from bson import ObjectId
from bson.json_util import dumps
import json
import bcrypt
import jwt
from functools import wraps
from flask_jwt_extended import JWTManager, jwt_required, get_jwt_identity, create_access_token, create_refresh_token, get_jwt
from config import config

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# JWT Configuration
app.config['JWT_SECRET_KEY'] = config['SECRET_KEY']
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(seconds=config['JWT_ACCESS_TOKEN_EXPIRES'])
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = datetime.timedelta(seconds=config['JWT_REFRESH_TOKEN_EXPIRES'])
app.config['JWT_BLACKLIST_ENABLED'] = True
app.config['JWT_BLACKLIST_TOKEN_CHECKS'] = ['access', 'refresh']

# Initialize JWT Manager
jwt_manager = JWTManager(app)

# MongoDB connection setup
def create_mongodb_connection():
    """Create MongoDB connection with error handling"""
    try:
        client = MongoClient(config['MONGODB_URI'], serverSelectionTimeoutMS=5000)
        # Test the connection
        client.admin.command('ping')
        print("MongoDB connection successful!")
        return client
    except (ConnectionFailure, ServerSelectionTimeoutError) as e:
        print(f"MongoDB connection failed: {e}")
        return None

# Initialize MongoDB client
mongodb_client = create_mongodb_connection()
db = mongodb_client.roadmap_db if mongodb_client else None

# Blacklist for storing revoked tokens
token_blacklist = set()

# Password validation function
def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    return True, "Password is valid"

# Password hashing functions
def hash_password(password):
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed):
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

# JWT token management functions
def generate_tokens(user_id, role):
    """Generate access and refresh tokens"""
    access_token = create_access_token(identity=str(user_id), additional_claims={'role': role})
    refresh_token = create_refresh_token(identity=str(user_id), additional_claims={'role': role})
    return access_token, refresh_token

def revoke_token(jti):
    """Add token to blacklist"""
    token_blacklist.add(jti)

def is_token_revoked(jwt_payload):
    """Check if token is revoked"""
    jti = jwt_payload['jti']
    return jti in token_blacklist

# Authentication middleware
def token_required(f):
    """Decorator to require valid JWT token"""
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        current_user = get_jwt_identity()
        claims = get_jwt()
        if is_token_revoked(claims):
            return jsonify({"error": "Token has been revoked"}), 401
        return f(current_user, *args, **kwargs)
    return decorated

# Admin role checking decorator
def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    @jwt_required()
    def decorated(*args, **kwargs):
        claims = get_jwt()
        if is_token_revoked(claims):
            return jsonify({"error": "Token has been revoked"}), 401
        if claims.get('role') != 'admin':
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    return jsonify({"message": "Welcome to the Roadmap Flask API with MongoDB"})

@app.route('/api/health')
def health_check():
    """Health check endpoint that includes database status"""
    db_status = "healthy" if mongodb_client else "unhealthy"
    return jsonify({
        "status": "healthy",
        "database": db_status,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
    })

@app.route('/api/roadmaps', methods=['GET'])
@token_required
def get_roadmaps(current_user_id):
    """Get all public roadmaps + user's roadmaps (authenticated)"""
    try:
        if not db:
            return jsonify({"error": "Database connection not available"}), 503

        roadmaps_collection = db.roadmaps
        claims = get_jwt()

        # Build query - show public roadmaps + user's own roadmaps
        query = {
            "$or": [
                {"is_public": True},
                {"created_by": ObjectId(current_user_id)}
            ]
        }

        # Admins can see all roadmaps
        if claims.get('role') == 'admin':
            query = {}

        roadmaps = list(roadmaps_collection.find(query))

        # Convert ObjectId to string for JSON serialization
        for roadmap in roadmaps:
            roadmap['_id'] = str(roadmap['_id'])
            if 'created_by' in roadmap:
                roadmap['created_by'] = str(roadmap['created_by'])

        return jsonify({"roadmaps": roadmaps})
    except Exception as e:
        return jsonify({"error": f"Failed to fetch roadmaps: {str(e)}"}), 500

@app.route('/api/roadmaps', methods=['POST'])
@token_required
def create_roadmap(current_user_id):
    """Create a new roadmap (authenticated users only)"""
    try:
        if not db:
            return jsonify({"error": "Database connection not available"}), 503

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        required_fields = ['title', 'description', 'category', 'difficulty_level', 'nodes']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"{field} is required"}), 400

        # Validate nodes array
        if not isinstance(data['nodes'], list) or len(data['nodes']) == 0:
            return jsonify({"error": "Nodes must be a non-empty array"}), 400

        # Validate each node has required fields
        for i, node in enumerate(data['nodes']):
            required_node_fields = ['id', 'title', 'description', 'position_x', 'position_y']
            for field in required_node_fields:
                if field not in node:
                    return jsonify({"error": f"Node {i} missing required field: {field}"}), 400

        # Set default values
        data['created_by'] = ObjectId(current_user_id)
        data['is_public'] = data.get('is_public', False)
        data['tags'] = data.get('tags', [])
        data['created_at'] = datetime.datetime.utcnow()
        data['updated_at'] = datetime.datetime.utcnow()

        # Set default completion status for nodes
        for node in data['nodes']:
            node['completed'] = False

        roadmaps_collection = db.roadmaps
        result = roadmaps_collection.insert_one(data)

        return jsonify({
            "message": "Roadmap created successfully",
            "id": str(result.inserted_id)
        }), 201
    except Exception as e:
        return jsonify({"error": f"Failed to create roadmap: {str(e)}"}), 500

@app.route('/api/roadmaps/<roadmap_id>', methods=['GET'])
@token_required
def get_roadmap(roadmap_id, current_user_id):
    """Get specific roadmap with node details and proper access control"""
    try:
        if not db:
            return jsonify({"error": "Database connection not available"}), 503

        roadmaps_collection = db.roadmaps
        claims = get_jwt()

        # Build query based on access control
        query = {"_id": ObjectId(roadmap_id)}
        if claims.get('role') != 'admin':
            # Non-admins can only see public roadmaps or their own
            query["$or"] = [
                {"is_public": True},
                {"created_by": ObjectId(current_user_id)}
            ]

        roadmap = roadmaps_collection.find_one(query)

        if not roadmap:
            return jsonify({"error": "Roadmap not found or access denied"}), 404

        # Convert ObjectId to string for JSON serialization
        roadmap['_id'] = str(roadmap['_id'])
        roadmap['created_by'] = str(roadmap['created_by'])

        return jsonify({"roadmap": roadmap})
    except Exception as e:
        return jsonify({"error": f"Failed to fetch roadmap: {str(e)}"}), 500

@app.route('/api/roadmaps/<roadmap_id>', methods=['PUT'])
@token_required
def update_roadmap(roadmap_id, current_user_id):
    """Update roadmap (owner or admin only)"""
    try:
        if not db:
            return jsonify({"error": "Database connection not available"}), 503

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        roadmaps_collection = db.roadmaps
        claims = get_jwt()

        # Check if roadmap exists and user has permission
        roadmap = roadmaps_collection.find_one({"_id": ObjectId(roadmap_id)})

        if not roadmap:
            return jsonify({"error": "Roadmap not found"}), 404

        # Check ownership or admin role
        if str(roadmap['created_by']) != current_user_id and claims.get('role') != 'admin':
            return jsonify({"error": "Access denied. Only owner or admin can update roadmap"}), 403

        # Add updated timestamp
        data['updated_at'] = datetime.datetime.utcnow()

        # Update the roadmap
        result = roadmaps_collection.update_one(
            {"_id": ObjectId(roadmap_id)},
            {"$set": data}
        )

        return jsonify({"message": "Roadmap updated successfully"})
    except Exception as e:
        return jsonify({"error": f"Failed to update roadmap: {str(e)}"}), 500

@app.route('/api/roadmaps/<roadmap_id>', methods=['DELETE'])
@token_required
def delete_roadmap(roadmap_id, current_user_id):
    """Delete roadmap (owner or admin only)"""
    try:
        if not db:
            return jsonify({"error": "Database connection not available"}), 503

        roadmaps_collection = db.roadmaps
        claims = get_jwt()

        # Check if roadmap exists and user has permission
        roadmap = roadmaps_collection.find_one({"_id": ObjectId(roadmap_id)})

        if not roadmap:
            return jsonify({"error": "Roadmap not found"}), 404

        # Check ownership or admin role
        if str(roadmap['created_by']) != current_user_id and claims.get('role') != 'admin':
            return jsonify({"error": "Access denied. Only owner or admin can delete roadmap"}), 403

        result = roadmaps_collection.delete_one({"_id": ObjectId(roadmap_id)})

        return jsonify({"message": "Roadmap deleted successfully"})
    except Exception as e:
        return jsonify({"error": f"Failed to delete roadmap: {str(e)}"}), 500

# ===== NODE-SPECIFIC ROUTES =====

@app.route('/api/roadmaps/<roadmap_id>/nodes/<node_id>/toggle', methods=['PUT'])
@token_required
def toggle_node_completion(roadmap_id, node_id, current_user_id):
    """Toggle node completion status"""
    try:
        if not db:
            return jsonify({"error": "Database connection not available"}), 503

        roadmaps_collection = db.roadmaps
        claims = get_jwt()

        # Check if roadmap exists and user has access
        roadmap = roadmaps_collection.find_one({"_id": ObjectId(roadmap_id)})

        if not roadmap:
            return jsonify({"error": "Roadmap not found"}), 404

        # Check access permissions (public roadmaps or user's own)
        if not roadmap.get('is_public', False) and str(roadmap['created_by']) != current_user_id and claims.get('role') != 'admin':
            return jsonify({"error": "Access denied"}), 403

        # Find the node and toggle its completion status
        nodes = roadmap.get('nodes', [])
        node_found = False

        for node in nodes:
            if str(node['id']) == node_id:
                node['completed'] = not node.get('completed', False)
                node_found = True
                break

        if not node_found:
            return jsonify({"error": "Node not found"}), 404

        # Update the roadmap with the modified nodes
        result = roadmaps_collection.update_one(
            {"_id": ObjectId(roadmap_id)},
            {"$set": {
                "nodes": nodes,
                "updated_at": datetime.datetime.utcnow()
            }}
        )

        # Find the updated node to return its new status
        updated_node = None
        for node in nodes:
            if str(node['id']) == node_id:
                updated_node = node
                break

        return jsonify({
            "message": "Node completion status updated",
            "node": updated_node
        })
    except Exception as e:
        return jsonify({"error": f"Failed to toggle node completion: {str(e)}"}), 500

@app.route('/api/roadmaps/<roadmap_id>/progress', methods=['GET'])
@token_required
def get_roadmap_progress(roadmap_id, current_user_id):
    """Get user progress for roadmap"""
    try:
        if not db:
            return jsonify({"error": "Database connection not available"}), 503

        roadmaps_collection = db.roadmaps
        claims = get_jwt()

        # Check if roadmap exists and user has access
        roadmap = roadmaps_collection.find_one({"_id": ObjectId(roadmap_id)})

        if not roadmap:
            return jsonify({"error": "Roadmap not found"}), 404

        # Check access permissions (public roadmaps or user's own)
        if not roadmap.get('is_public', False) and str(roadmap['created_by']) != current_user_id and claims.get('role') != 'admin':
            return jsonify({"error": "Access denied"}), 403

        nodes = roadmap.get('nodes', [])
        total_nodes = len(nodes)
        completed_nodes = sum(1 for node in nodes if node.get('completed', False))

        progress_data = {
            "roadmap_id": str(roadmap['_id']),
            "total_nodes": total_nodes,
            "completed_nodes": completed_nodes,
            "progress_percentage": (completed_nodes / total_nodes * 100) if total_nodes > 0 else 0,
            "completed_nodes_list": [node for node in nodes if node.get('completed', False)],
            "pending_nodes_list": [node for node in nodes if not node.get('completed', False)]
        }

        return jsonify({"progress": progress_data})
    except Exception as e:
        return jsonify({"error": f"Failed to fetch progress: {str(e)}"}), 500

# ===== ADMIN-ONLY ROUTES =====

@app.route('/api/admin/roadmaps', methods=['GET'])
@admin_required
def get_all_roadmaps_admin():
    """Get all roadmaps (admin only)"""
    try:
        if not db:
            return jsonify({"error": "Database connection not available"}), 503

        roadmaps_collection = db.roadmaps
        roadmaps = list(roadmaps_collection.find({}))

        # Convert ObjectId to string for JSON serialization
        for roadmap in roadmaps:
            roadmap['_id'] = str(roadmap['_id'])
            if 'created_by' in roadmap:
                roadmap['created_by'] = str(roadmap['created_by'])

        return jsonify({"roadmaps": roadmaps})
    except Exception as e:
        return jsonify({"error": f"Failed to fetch roadmaps: {str(e)}"}), 500

@app.route('/api/admin/roadmaps/<roadmap_id>/force', methods=['DELETE'])
@admin_required
def force_delete_roadmap(roadmap_id):
    """Force delete any roadmap (admin only)"""
    try:
        if not db:
            return jsonify({"error": "Database connection not available"}), 503

        roadmaps_collection = db.roadmaps
        result = roadmaps_collection.delete_one({"_id": ObjectId(roadmap_id)})

        if result.deleted_count == 0:
            return jsonify({"error": "Roadmap not found"}), 404

        return jsonify({"message": "Roadmap force deleted successfully by admin"})
    except Exception as e:
        return jsonify({"error": f"Failed to force delete roadmap: {str(e)}"}), 500

# ===== AUTHENTICATION ROUTES =====

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    """User registration endpoint"""
    try:
        if not db:
            return jsonify({"error": "Database connection not available"}), 503

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        required_fields = ['username', 'email', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"{field} is required"}), 400

        username = data['username'].strip()
        email = data['email'].strip().lower()
        password = data['password']

        # Validate input lengths
        if len(username) < 3:
            return jsonify({"error": "Username must be at least 3 characters long"}), 400
        if len(email) < 5 or '@' not in email:
            return jsonify({"error": "Valid email is required"}), 400

        # Validate password strength
        is_valid, password_message = validate_password(password)
        if not is_valid:
            return jsonify({"error": password_message}), 400

        # Check if user already exists
        users_collection = db.users
        existing_user = users_collection.find_one({"$or": [
            {"username": username},
            {"email": email}
        ]})

        if existing_user:
            if existing_user['username'] == username:
                return jsonify({"error": "Username already exists"}), 409
            else:
                return jsonify({"error": "Email already exists"}), 409

        # Hash password
        hashed_password = hash_password(password)

        # Create user document
        user_doc = {
            "username": username,
            "email": email,
            "password": hashed_password,
            "role": data.get('role', 'user'),  # Default to 'user' if not specified
            "created_at": datetime.datetime.utcnow(),
            "updated_at": datetime.datetime.utcnow()
        }

        # Insert user
        result = users_collection.insert_one(user_doc)

        # Generate tokens
        access_token, refresh_token = generate_tokens(result.inserted_id, user_doc['role'])

        return jsonify({
            "message": "User created successfully",
            "user": {
                "id": str(result.inserted_id),
                "username": username,
                "email": email,
                "role": user_doc['role']
            },
            "access_token": access_token,
            "refresh_token": refresh_token
        }), 201

    except Exception as e:
        return jsonify({"error": f"Registration failed: {str(e)}"}), 500

@app.route('/api/auth/login', methods=['POST'])
def login():
    """User login endpoint"""
    try:
        if not db:
            return jsonify({"error": "Database connection not available"}), 503

        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        if 'email' not in data or 'password' not in data:
            return jsonify({"error": "Email and password are required"}), 400

        email = data['email'].strip().lower()
        password = data['password']

        # Find user
        users_collection = db.users
        user = users_collection.find_one({"email": email})

        if not user:
            return jsonify({"error": "Invalid email or password"}), 401

        # Verify password
        if not check_password(password, user['password']):
            return jsonify({"error": "Invalid email or password"}), 401

        # Generate tokens
        access_token, refresh_token = generate_tokens(user['_id'], user['role'])

        return jsonify({
            "message": "Login successful",
            "user": {
                "id": str(user['_id']),
                "username": user['username'],
                "email": user['email'],
                "role": user['role']
            },
            "access_token": access_token,
            "refresh_token": refresh_token
        }), 200

    except Exception as e:
        return jsonify({"error": f"Login failed: {str(e)}"}), 500

@app.route('/api/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    """User logout endpoint - revoke tokens"""
    try:
        claims = get_jwt()
        jti = claims['jti']
        revoke_token(jti)

        return jsonify({"message": "Successfully logged out"}), 200

    except Exception as e:
        return jsonify({"error": f"Logout failed: {str(e)}"}), 500

@app.route('/api/auth/profile', methods=['GET'])
@token_required
def get_profile(current_user_id):
    """Get user profile (protected route)"""
    try:
        if not db:
            return jsonify({"error": "Database connection not available"}), 503

        users_collection = db.users
        user = users_collection.find_one({"_id": ObjectId(current_user_id)})

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Remove password from response
        user_data = {
            "id": str(user['_id']),
            "username": user['username'],
            "email": user['email'],
            "role": user['role'],
            "created_at": user['created_at'].isoformat() if user.get('created_at') else None,
            "updated_at": user['updated_at'].isoformat() if user.get('updated_at') else None
        }

        return jsonify({"user": user_data}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch profile: {str(e)}"}), 500

@app.route('/api/auth/refresh', methods=['POST'])
@jwt_required()
def refresh_token():
    """Refresh access token"""
    try:
        current_user = get_jwt_identity()
        claims = get_jwt()

        # Get user to retrieve role
        if not db:
            return jsonify({"error": "Database connection not available"}), 503

        users_collection = db.users
        user = users_collection.find_one({"_id": ObjectId(current_user)})

        if not user:
            return jsonify({"error": "User not found"}), 404

        # Generate new access token
        new_access_token = create_access_token(
            identity=current_user,
            additional_claims={'role': user['role']}
        )

        return jsonify({
            "access_token": new_access_token,
            "message": "Token refreshed successfully"
        }), 200

    except Exception as e:
        return jsonify({"error": f"Token refresh failed: {str(e)}"}), 500

@app.route('/api/auth/admin/users', methods=['GET'])
@admin_required
def get_all_users():
    """Get all users (admin only)"""
    try:
        if not db:
            return jsonify({"error": "Database connection not available"}), 503

        users_collection = db.users
        users = list(users_collection.find({}))

        # Convert ObjectId to string and remove passwords
        for user in users:
            user['_id'] = str(user['_id'])
            user.pop('password', None)

        return jsonify({"users": users}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to fetch users: {str(e)}"}), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == '__main__':
    app.run(
        host=config['HOST'],
        port=config['PORT'],
        debug=config['DEBUG']
    )