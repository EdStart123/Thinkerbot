# AI-enabled Bot for Thinkering Collective Fellows
# This is a conceptual Python-based backend bot architecture using FastAPI and SQLAlchemy
# You can adapt this for use in Retool, Bubble, or any frontend you use

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import openai

# Database setup
DATABASE_URL = "sqlite:///./thinkering_fellowship.db"  # Switch to Postgres or another in production
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# OpenAI API Key
openai.api_key = "your_openai_api_key_here"

# Data models
class LearningLog(Base):
    __tablename__ = "learning_logs"
    id = Column(Integer, primary_key=True, index=True)
    fellow_name = Column(String, index=True)
    entry = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

# FastAPI app
app = FastAPI()

# Pydantic schema for input validation
class LogEntry(BaseModel):
    fellow_name: str
    entry: str

# Route to log new entry
@app.post("/log")
def create_log(log: LogEntry):
    db = SessionLocal()
    new_log = LearningLog(fellow_name=log.fellow_name, entry=log.entry)
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    db.close()
    return {"status": "success", "log_id": new_log.id}

# Route to generate AI summary
@app.get("/summary/{fellow_name}")
def get_summary(fellow_name: str):
    db = SessionLocal()
    logs = db.query(LearningLog).filter(LearningLog.fellow_name == fellow_name).all()
    db.close()
    if not logs:
        raise HTTPException(status_code=404, detail="No logs found for this fellow")
    combined_entries = "\n".join([log.entry for log in logs])

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a learning coach summarizing fellowship progress."},
            {"role": "user", "content": f"Summarize the following learning reflections:\n{combined_entries}"}
        ]
    )
    return {"summary": response.choices[0].message['content']}

# Optional: route to return learning timeline
@app.get("/timeline/{fellow_name}")
def get_timeline(fellow_name: str):
    db = SessionLocal()
    logs = db.query(LearningLog).filter(LearningLog.fellow_name == fellow_name).order_by(LearningLog.timestamp).all()
    db.close()
    return [{"timestamp": log.timestamp.isoformat(), "entry": log.entry} for log in logs]
