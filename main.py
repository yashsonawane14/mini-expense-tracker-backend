from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from database import SessionLocal, engine
import models
import jwt
from collections import defaultdict
from datetime import datetime, timedelta
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer

app = FastAPI()
models.Base.metadata.create_all(bind=engine)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Dependency for DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ✅ User models
class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# ✅ Decode JWT and get current user
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user = db.query(models.User).filter(models.User.email == payload["sub"]).first()
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ✅ Register User
@app.post("/register")
def register_user(user: UserCreate, db: Session = Depends(get_db)):
    existing_user = db.query(models.User).filter(models.User.email == user.email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = pwd_context.hash(user.password)
    new_user = models.User(
        first_name=user.first_name,
        last_name=user.last_name,
        email=user.email,
        hashed_password=hashed_password
    )
    db.add(new_user)
    db.commit()
    return {"message": "User registered successfully"}

# ✅ Login API
@app.post("/login")
def login_user(user_data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == user_data.email).first()
    
    if not user or not pwd_context.verify(user_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token_expiration = datetime.utcnow() + timedelta(hours=12)
    token_payload = {"sub": user.email, "exp": token_expiration.timestamp()}
    token = jwt.encode(token_payload, SECRET_KEY, algorithm=ALGORITHM)

    return {"access_token": token, "token_type": "bearer"}

# ✅ Expense model for request
class ExpenseCreate(BaseModel):
    amount: float
    category: str
    description: str = None
    date: datetime

# ✅ Add Expense API
@app.post("/expenses")
def add_expense(expense: ExpenseCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    new_expense = models.Expense(
        amount=expense.amount,
        category=expense.category,
        description=expense.description,
        date=expense.date,
        user_id=user.id
    )
    db.add(new_expense)
    db.commit()
    db.refresh(new_expense)
    return {"message": "Expense added successfully", "expense": new_expense}

# ✅ Get Expenses (Pagination & Filtering)
@app.get("/expenses")
def get_expenses(
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
    page: int = Query(1, alias="page", ge=1),
    limit: int = Query(5, alias="limit", ge=1, le=50),
    category: str = Query(None, alias="category"),
    start_date: str = Query(None, alias="start_date"),
    end_date: str = Query(None, alias="end_date"),
):
    query = db.query(models.Expense).filter(models.Expense.user_id == user.id)

    if category:
        query = query.filter(models.Expense.category == category)

    if start_date and end_date:
        query = query.filter(
            models.Expense.date.between(start_date, end_date)
        )

    total_expenses = query.count()
    expenses = query.offset((page - 1) * limit).limit(limit).all()

    return {"total": total_expenses, "expenses": expenses}

# ✅ Get Expense Insights
@app.get("/expenses/analytics")
def get_expense_analytics(user=Depends(get_current_user), db: Session = Depends(get_db)):
    query = db.query(models.Expense).filter(models.Expense.user_id == user.id).all()

    # ✅ Total Expense
    total_expense = sum(expense.amount for expense in query)

    # ✅ Category-wise Expense Breakdown
    category_data = defaultdict(float)
    for expense in query:
        category_data[expense.category] += expense.amount
    category_wise = [{"category": cat, "amount": amt} for cat, amt in category_data.items()]

    # ✅ Monthly Expense Trend
    monthly_data = defaultdict(float)
    for expense in query:
        month = expense.date.strftime("%Y-%m")
        monthly_data[month] += expense.amount
    monthly_trend = [{"month": m, "amount": amt} for m, amt in sorted(monthly_data.items())]

    return {
        "total": total_expense,
        "categoryWise": category_wise,
        "monthlyTrend": monthly_trend
    }

# ✅ Delete Expense API
@app.delete("/expenses/{expense_id}")
def delete_expense(expense_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    expense = db.query(models.Expense).filter(models.Expense.id == expense_id, models.Expense.user_id == user.id).first()

    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    db.delete(expense)
    db.commit()
    return {"message": "Expense deleted successfully"}

# ✅ Update Expense API
@app.put("/expenses/{expense_id}")
def update_expense(expense_id: int, updated_expense: ExpenseCreate, user=Depends(get_current_user), db: Session = Depends(get_db)):
    expense = db.query(models.Expense).filter(models.Expense.id == expense_id, models.Expense.user_id == user.id).first()
    
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    expense.amount = updated_expense.amount
    expense.category = updated_expense.category
    expense.description = updated_expense.description
    expense.date = updated_expense.date
    
    db.commit()
    db.refresh(expense)

    return {"message": "Expense updated successfully", "expense": expense}
