from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from typing import Optional
import mysql.connector
import jwt
from datetime import datetime, timedelta
import hashlib
import os
from dotenv import load_dotenv
from passlib.context import CryptContext


load_dotenv()

# Initialize FastAPI app
app = FastAPI(title="User Authentication API")

origins = [
    "http://localhost:5173",  # React Dev Server
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # อนุญาตทุก domain
    allow_credentials=True,
    allow_methods=["*"],  # อนุญาตทุก method
    allow_headers=["*"],  # อนุญาตทุก header
)
# Database Configuration
DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST") ,
    "user": os.getenv("MYSQL_USER") ,
    "password": os.getenv("MYSQL_PASSWORD") ,  # Replace with your MySQL password
    "database": os.getenv("MYSQL_DATABASE") 
}

# JWT Configuration
SECRET_KEY = os.environ.get("SECRET_KEY", "your_secret_key") # Change in production
ALGORITHM = os.getenv("ALGORITHM") 
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")) 

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Models
class UserBase(BaseModel):
    username: str

class UserCreate(UserBase):
    password: str

class UserUpdate(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None

class UserInDB(UserBase):
    id: int
    hashed_password: str
    visits: int

class User(UserBase):
    id: int
    visits: int

class Token(BaseModel):
    access_token: str
    token_type: str

# Database functions
def get_db_connection():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        return conn
    except mysql.connector.Error as err:
        print(f"Database connection error: {err}")
        raise HTTPException(status_code=500, detail="Database connection error")

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create users table if it doesn't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INT AUTO_INCREMENT PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password VARCHAR(255) NOT NULL,
        visits INT DEFAULT 0
    )
    """)
    
    conn.commit()
    cursor.close()
    conn.close()

# Password functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

# User functions
def get_user(username: str):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if user:
        return UserInDB(
            id=user["id"],
            username=user["username"],
            hashed_password=user["password"],
            visits=user["visits"]
        )
    return None

def authenticate_user(username: str, password: str):
    user = get_user(username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def increment_visit_count(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("UPDATE users SET visits = visits + 1 WHERE id = %s", (user_id,))
    
    conn.commit()
    cursor.close()
    conn.close()

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception
    
    user = get_user(username)
    if user is None:
        raise credentials_exception
    
    increment_visit_count(user.id)
    return user

# Endpoints
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    print(form_data.username, form_data.password)
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/register", status_code=status.HTTP_201_CREATED) 
async def register_user(user: UserCreate):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if user already exists
    existing_user = get_user(user.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    hashed_password = get_password_hash(user.password)
    
    try:
        cursor.execute(
            "INSERT INTO users (username, password, visits) VALUES (%s, %s, %s)",
            (user.username, hashed_password, 0)
        )
        conn.commit()
    except mysql.connector.Error as err:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register user: {err}"
        )
    finally:
        cursor.close()
        conn.close()
    
    return {"message": "User registered successfully"}

@app.get("/users/me", response_model=User)
async def read_users_me(current_user: UserInDB = Depends(get_current_user)):
    return User(
        id=current_user.id,
        username=current_user.username,
        visits=current_user.visits
    )

@app.put("/users/me", response_model=User)
async def update_user(
    user_update: UserUpdate,
    current_user: UserInDB = Depends(get_current_user)
):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    updates = []
    values = []
    
    if user_update.username:
        # Check if new username already exists
        if user_update.username != current_user.username:
            existing_user = get_user(user_update.username)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username already taken"
                )
        updates.append("username = %s")
        values.append(user_update.username)
    
    if user_update.password:
        updates.append("password = %s")
        values.append(get_password_hash(user_update.password))
    
    if not updates:
        return User(
            id=current_user.id,
            username=current_user.username,
            visits=current_user.visits
        )
    
    values.append(current_user.id)
    
    try:
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = %s"
        cursor.execute(query, values)
        conn.commit()
    except mysql.connector.Error as err:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {err}"
        )
    finally:
        cursor.close()
        conn.close()
    
    # Get updated user info
    updated_user = get_user(user_update.username if user_update.username else current_user.username)
    
    return User(
        id=updated_user.id,
        username=updated_user.username,
        visits=updated_user.visits
    )

@app.delete("/users/me", status_code=status.HTTP_200_OK)
async def delete_user(current_user: UserInDB = Depends(get_current_user)):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("DELETE FROM users WHERE id = %s", (current_user.id,))
        conn.commit()
    except mysql.connector.Error as err:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {err}"
        )
    finally:
        cursor.close()
        conn.close()
    
    return {"message": "User deleted successfully"}

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)