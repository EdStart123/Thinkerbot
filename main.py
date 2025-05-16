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
from openai import OpenAI
import time

client = OpenAI(api_key="your_openai_api_key_here")

@app.get("/summary/{fellow_name}")
def get_summary(fellow_name: str):
    db = SessionLocal()
    logs = db.query(LearningLog).filter(LearningLog.fellow_name == fellow_name).all()
    db.close()
    if not logs:
        raise HTTPException(status_code=404, detail="No logs found for this fellow")

    combined_entries = "\n".join([log.entry for log in logs])

    assistant_id = "asst_abc123..."  # ⬅️ Replace this with your actual Assistant ID

    thread = client.beta.threads.create()

    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=f"Summarize the following learning reflections:\n{combined_entries}"
    )

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id,
    )

    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run_status.status == "completed":
            break
        elif run_status.status == "failed":
            raise Exception("Assistant run failed")
        time.sleep(1)

    messages = client.beta.threads.messages.list(thread_id=thread.id)
    assistant_message = next(
        (msg for msg in messages.data if msg.role == "assistant"), None
    )

    if assistant_message:
        return {"summary": assistant_message.content[0].text.value}
    else:
        raise HTTPException(status_code=500, detail="No assistant response found")


# Optional: route to return learning timeline
@app.get("/timeline/{fellow_name}")
def get_timeline(fellow_name: str):
    db = SessionLocal()
    logs = db.query(LearningLog).filter(LearningLog.fellow_name == fellow_name).order_by(LearningLog.timestamp).all()
    db.close()
    return [{"timestamp": log.timestamp.isoformat(), "entry": log.entry} for log in logs]
