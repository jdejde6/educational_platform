# /home/ubuntu/educational_platform/backend/educational_platform_backend/src/routes/auth.py
import os
from flask import Blueprint, request, jsonify
from ..models.user import User, db # Assuming models.user is in the same directory level
import pyotp # For TOTP MFA
import base64 # For OTP secret encoding
import requests # For CAPTCHA verification

# WebAuthn library imports
from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
    base64url_to_bytes,
)
from webauthn.helpers.structs import (
    RegistrationCredential,
    AuthenticationCredential,
    AuthenticatorSelectionCriteria,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

# Configuration (replace with your actual values or load from environment variables)
RP_ID = os.getenv("RP_ID", "localhost")  # Relying Party ID (your domain)
RP_NAME = os.getenv("RP_NAME", "Educational Platform")
ORIGIN = os.getenv("ORIGIN", "http://localhost:3000") # Frontend origin
HCAPTCHA_SECRET_KEY = os.getenv("HCAPTCHA_SECRET_KEY", "your_hcaptcha_secret_key") # Replace with your hCaptcha secret key
HCAPTCHA_VERIFY_URL = "https://hcaptcha.com/siteverify"

# In-memory store for challenges (in a real app, use a persistent store like Redis or your database)
challenge_store = {}
user_credentials_store = {} # Store user_id -> [credential_id_bytes, public_key_bytes, sign_count]

# --- CAPTCHA Verification Helper ---
def verify_captcha(captcha_response):
    if not HCAPTCHA_SECRET_KEY or HCAPTCHA_SECRET_KEY == "your_hcaptcha_secret_key":
        print("Warning: HCAPTCHA_SECRET_KEY is not set. Skipping CAPTCHA verification for development.")
        return True # Skip in dev if not configured
    payload = {
        "response": captcha_response,
        "secret": HCAPTCHA_SECRET_KEY
    }
    try:
        response = requests.post(HCAPTCHA_VERIFY_URL, data=payload, timeout=5)
        response.raise_for_status() # Raise an exception for HTTP errors
        return response.json().get("success", False)
    except requests.exceptions.RequestException as e:
        print(f"CAPTCHA verification failed: {e}")
        return False

# --- Registration ---
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    captcha_token = data.get("captcha_token")

    if not username or not email or not password:
        return jsonify({"message": "Missing username, email, or password"}), 400
    
    if not captcha_token:
        return jsonify({"message": "CAPTCHA token is required"}), 400

    if not verify_captcha(captcha_token):
        return jsonify({"message": "Invalid CAPTCHA"}), 400

    if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
        return jsonify({"message": "User already exists"}), 409

    new_user = User(username=username, email=email)
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "User registered successfully", "user_id": new_user.id}), 201

# --- Basic Login ---
@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = User.query.filter_by(username=username).first()

    if user and user.check_password(password):
        if user.is_mfa_enabled:
            return jsonify({"message": "Login successful, MFA required", "mfa_required": True, "user_id": user.id}), 200
        
        # For WebAuthn, we might want to offer it as a second factor or primary login method
        # For simplicity, let's assume password login is primary for now.
        # If WebAuthn is registered, we could potentially skip password or offer it.
        
        # Placeholder for JWT token generation
        return jsonify({"message": "Login successful", "mfa_required": False, "user_id": user.id, "token": "dummy_jwt_token"}), 200
    
    return jsonify({"message": "Invalid credentials"}), 401

# --- MFA (TOTP) Routes ---
@auth_bp.route("/mfa/setup", methods=["POST"])
def mfa_setup_start():
    data = request.get_json()
    user_id = data.get("user_id")
    user = User.query.get(user_id)

    if not user:
        return jsonify({"message": "User not found"}), 404

    if not user.otp_secret: # Generate only if not already set
        user.otp_secret = base64.b32encode(os.urandom(10)).decode("utf-8")
        db.session.commit()
    
    provisioning_uri = pyotp.totp.TOTP(user.otp_secret).provisioning_uri(
        name=user.email, 
        issuer_name=RP_NAME
    )
    
    return jsonify({
        "message": "Scan the QR code with your authenticator app.",
        "otp_secret": user.otp_secret,
        "provisioning_uri": provisioning_uri
    }), 200

@auth_bp.route("/mfa/verify", methods=["POST"])
def mfa_setup_verify():
    data = request.get_json()
    user_id = data.get("user_id")
    otp_token = data.get("otp_token")

    user = User.query.get(user_id)

    if not user or not user.otp_secret:
        return jsonify({"message": "User not found or MFA not initiated"}), 404

    totp = pyotp.TOTP(user.otp_secret)
    if totp.verify(otp_token):
        user.is_mfa_enabled = True
        db.session.commit()
        return jsonify({"message": "MFA enabled successfully"}), 200
    else:
        return jsonify({"message": "Invalid OTP token"}), 400

@auth_bp.route("/mfa/login", methods=["POST"])
def mfa_login_verify():
    data = request.get_json()
    user_id = data.get("user_id")
    otp_token = data.get("otp_token")

    user = User.query.get(user_id)

    if not user or not user.is_mfa_enabled or not user.otp_secret:
        return jsonify({"message": "User not found or MFA not enabled for this user"}), 404

    totp = pyotp.TOTP(user.otp_secret)
    if totp.verify(otp_token):
        # Placeholder for JWT token generation
        return jsonify({"message": "MFA verification successful, logged in", "token": "dummy_jwt_token_after_mfa"}), 200
    else:
        return jsonify({"message": "Invalid OTP token"}), 400

# --- WebAuthn Routes ---
@auth_bp.route("/webauthn/register-options", methods=["POST"])
def webauthn_register_options_route():
    data = request.get_json()
    user_id = data.get("user_id") # Assuming user is already created via password registration
    username = data.get("username")

    user = User.query.get(user_id)
    if not user or user.username != username:
        return jsonify({"message": "User not found or username mismatch"}), 404

    # For simplicity, we are not storing existing credential IDs for exclusion here.
    # In a real app, you should retrieve existing credential IDs for this user.
    # existing_credentials = user_credentials_store.get(str(user_id), [])
    # exclude_credentials = [{ "type": "public-key", "id": cred[0] } for cred in existing_credentials]

    options = generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        user_id=str(user.id).encode("utf-8"), # User ID must be bytes
        user_name=user.username,
        user_display_name=user.username,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED, # Or REQUIRED / DISCOURAGED
            user_verification=UserVerificationRequirement.PREFERRED, # Or REQUIRED / DISCOURAGED
        )
        # exclude_credentials=exclude_credentials # To prevent re-registration of same authenticator
    )

    challenge_store[str(user_id)] = options.challenge # Store challenge
    return jsonify(options_to_json(options)), 200

@auth_bp.route("/webauthn/register-verify", methods=["POST"])
def webauthn_register_verify_route():
    data = request.get_json()
    user_id = data.get("user_id")
    
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404

    challenge = challenge_store.pop(str(user_id), None)
    if not challenge:
        return jsonify({"message": "Challenge not found or expired"}), 400

    try:
        registration_verification = verify_registration_response(
            credential=RegistrationCredential.parse_raw(request.data),
            expected_challenge=challenge,
            expected_origin=ORIGIN,
            expected_rp_id=RP_ID,
            require_user_verification=False # Set based on your policy
        )
        
        # Store the credential. In a real app, this would be in a database linked to the user.
        # For this example, using a simple in-memory store.
        if str(user_id) not in user_credentials_store:
            user_credentials_store[str(user_id)] = []
        
        user_credentials_store[str(user_id)].append([
            registration_verification.credential_id,
            registration_verification.credential_public_key,
            registration_verification.sign_count
        ])
        # Here you would typically mark in your DB that the user has a WebAuthn credential.
        # For example: user.has_webauthn_credential = True; db.session.commit()

        return jsonify({"verified": True, "message": "WebAuthn credential registered successfully"}), 200
    except Exception as e:
        return jsonify({"verified": False, "message": f"Registration verification failed: {str(e)}"}), 400

@auth_bp.route("/webauthn/login-options", methods=["POST"])
def webauthn_login_options_route():
    data = request.get_json()
    username = data.get("username") # User might provide username to find their credentials
    
    user = User.query.filter_by(username=username).first()
    if not user:
        # If username is not provided, or user not found, we can do a discoverable credential request
        # This is also known as "passwordless" login if no username is required upfront.
        options = generate_authentication_options(
            rp_id=RP_ID,
            user_verification=UserVerificationRequirement.PREFERRED
        )
        challenge_store["anonymous_login"] = options.challenge # Store challenge for anonymous login
        return jsonify(options_to_json(options)), 200

    # If user is found, get their registered credentials
    user_id_str = str(user.id)
    if user_id_str not in user_credentials_store or not user_credentials_store[user_id_str]:
        return jsonify({"message": "No WebAuthn credentials registered for this user"}), 404

    allow_credentials = [
        {"type": "public-key", "id": cred[0]} for cred in user_credentials_store[user_id_str]
    ]

    options = generate_authentication_options(
        rp_id=RP_ID,
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.PREFERRED
    )

    challenge_store[user_id_str] = options.challenge # Store challenge
    return jsonify(options_to_json(options)), 200

@auth_bp.route("/webauthn/login-verify", methods=["POST"])
def webauthn_login_verify_route():
    data = request.get_json()
    username = data.get("username") # Optional, client might send it back
    
    user = None
    user_id_str = None
    raw_id_bytes = base64url_to_bytes(data["rawId"])

    # Try to find user by credential ID (if discoverable credential / passkey)
    # This requires iterating through your stored credentials to find a match for raw_id_bytes
    # This is a simplified lookup; a real app needs an efficient way to find user by credential ID.
    found_user_id = None
    for uid, creds in user_credentials_store.items():
        for cred_info in creds:
            if cred_info[0] == raw_id_bytes:
                found_user_id = uid
                user = User.query.get(found_user_id)
                break
        if found_user_id:
            break
    
    if not user and username:
        user = User.query.filter_by(username=username).first()

    if not user:
        return jsonify({"verified": False, "message": "User not found or credential not recognized"}), 404

    user_id_str = str(user.id)
    challenge = challenge_store.pop(user_id_str, challenge_store.pop("anonymous_login", None))
    if not challenge:
        return jsonify({"verified": False, "message": "Challenge not found or expired"}), 400

    # Find the specific credential used for login from the user's stored credentials
    credential_to_verify = None
    if user_id_str in user_credentials_store:
        for cred_info in user_credentials_store[user_id_str]:
            if cred_info[0] == raw_id_bytes:
                credential_to_verify = cred_info
                break
    
    if not credential_to_verify:
         return jsonify({"verified": False, "message": "Credential not found for user"}), 400

    try:
        authentication_verification = verify_authentication_response(
            credential=AuthenticationCredential.parse_raw(request.data),
            expected_challenge=challenge,
            expected_origin=ORIGIN,
            expected_rp_id=RP_ID,
            credential_public_key=credential_to_verify[1],
            credential_current_sign_count=credential_to_verify[2],
            require_user_verification=False # Set based on your policy
        )

        # Update the sign count for the credential
        credential_to_verify[2] = authentication_verification.new_sign_count
        # In a real app, save this new_sign_count to your database.

        # Placeholder for JWT token generation
        return jsonify({"verified": True, "message": "WebAuthn login successful", "user_id": user.id, "token": "dummy_jwt_token_webauthn"}), 200
    except Exception as e:
        return jsonify({"verified": False, "message": f"Authentication verification failed: {str(e)}"}), 400

