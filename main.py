from flask import Flask, render_template, request, redirect, url_for, jsonify
import openai
import shelve
import os
from dotenv import load_dotenv
import markdown2

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise ValueError("OPENAI_API_KEY is not set. Check your .env file.")

client = openai.OpenAI(api_key=api_key)

app = Flask(__name__)

SYSTEM_PROMPT_PATH = "system_prompt.txt"
try:
    with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
        system_prompt = f.read().strip()
except FileNotFoundError:
    raise FileNotFoundError(f"System prompt file '{SYSTEM_PROMPT_PATH}' not found.")

SESSION_DB = "chat_history.db"


def get_chat_history():
    """Retrieve chat history from shelve database."""
    with shelve.open(SESSION_DB) as db:
        return db.get("history", [{"role": "system", "content": system_prompt}])
    
    
def save_chat_history(history):
    """Save chat history to shelve database."""
    with shelve.open(SESSION_DB) as db:
        db["history"] = history
    
    
def clear_chat_history():
    """Clear chat history from shelve database."""
    for ext in [".bak", ".dat", ".dir"]:
        try:
            os.remove(SESSION_DB + ext)
        except FileNotFoundError:
            pass
    
    
def call_openai_api(text: str) -> str:
    """Sends user input to OpenAI API and returns the response."""
    chat_history = get_chat_history()
    chat_history.append({"role": "user", "content": text})
    
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=chat_history,
    )
    
    assistant_reply = response.choices[0].message.content.strip()
    chat_history.append({"role": "assistant", "content": assistant_reply})
    save_chat_history(chat_history)
    return assistant_reply
    
    
@app.route("/")
def index():
    return render_template("index.html")
    
    
@app.route("/results", methods=["GET", "POST"])
def results():
    
    name = request.form.get("name", "Guest User")
    birthdate = request.form.get("birthdate", "Not provided")
    raasi = request.form.get("raasi", "")  # Default to an empty string if not provided
    place_of_birth = request.form.get("place_of_birth", "Not provided")
    time_of_birth = request.form.get("time_of_birth", "Not provided")
    
    # Combine inputs into a single prompt for the LLM
    prompt = (
        f"Generate a personalized astrology reading for:\n"
        f"Name: {name}\n"
        f"Date of Birth: {birthdate}\n"
        f"Raasi (Zodiac Sign): {raasi or 'Not selected'}\n"
        f"Place of Birth: {place_of_birth}\n"
        f"Time of Birth: {time_of_birth}\n"
    )
    
    ai_response = ""
    try:
        ai_response = call_openai_api(prompt)
        ai_response = markdown2.markdown(ai_response)  # Convert Markdown to HTML
    except Exception as e:
        ai_response = f"<p>Error: {str(e)}</p>"
    
    return render_template(
        "results.html",
        name=name,
        birthdate=birthdate,
        raasi=raasi,
        place_of_birth=place_of_birth,
        time_of_birth=time_of_birth,
        ai_response=ai_response,
    )
    
    
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    user_input = data.get("text", "")
    if not user_input:
        return jsonify({"error": "No input provided"}), 400
    
    try:
        response = call_openai_api(user_input)
        return jsonify({"response": response})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    
@app.route("/api/clear_history", methods=["POST"])
def clear_history():
    clear_chat_history()
    return jsonify({"message": "Chat history cleared"})
    
    
if __name__ == "__main__":
    app.run(debug=True)
