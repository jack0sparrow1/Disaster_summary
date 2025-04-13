import requests
import re
from flask import Flask, request, jsonify
from groq import Groq
from dotenv import load_dotenv
import os

load_dotenv()

# Get API keys from environment variables
SERP_API_KEY = os.getenv("SERP_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# ---- Function: Search Web via SerpAPI ----
def search_disaster_topic(query):
    url = "https://serpapi.com/search"
    params = {
        "q": query,
        "api_key": SERP_API_KEY,
        "engine": "google",
        "hl": "en",
        "num": 10
    }

    try:
        response = requests.get(url, params=params)
        results = response.json().get("organic_results", [])
        return results
    except Exception as e:
        return []

# ---- Function: Summarize Web Search Results ----
def summarize_search_results(results, topic):
    if not results:
        return "❌ No recent search results available for this topic."

    topic_keywords = re.findall(r'\w+', topic.lower())

    def is_relevant(res):
        text = f"{res.get('title', '')} {res.get('snippet', '')}".lower()
        return any(keyword in text for keyword in topic_keywords)

    filtered = [res for res in results if 'title' in res and 'snippet' in res and is_relevant(res)]
    used_results = filtered if len(filtered) >= 3 else results

    context = "\n\n".join(
        [f"Title: {res['title']}\nSnippet: {res['snippet']}" for res in used_results if 'title' in res and 'snippet' in res]
    )

    prompt = f"""
You are a disaster response analyst AI.

Your job is to write a **3-paragraph professional summary** about the disaster topic: "{topic}", based on the following real-time search results. This summary will be reviewed by DAO members who are evaluating whether to approve a donation campaign for the affected region.

🧠 Keep in mind:
- Give "spaces" between the words in the output you provide and make it look beautiful.Remember the spaces
- Be factual, emotionally compelling, and easy to understand.
- Clearly convey the severity, scale, and urgency.
- Suggest concrete reasons why humanitarian aid is necessary.
- Include rough funding estimates **in USD** even if exact figures are unavailable.

📝 Structure the summary as follows:

1. **What happened**: Briefly explain the nature of the disaster, including the type, location, and timing. Highlight any unusual or alarming aspects.
2. **Who is affected**: Describe the scale of the disaster’s impact, including estimated number of people affected, vulnerable populations (e.g. children, elderly), and damage to homes, infrastructure, or essential services.
3. **Help required**: Recommend the types of aid that should be prioritized (e.g. emergency medical services, shelter, food, financial relief). Based on the data or your best judgment, provide a reasonable funding estimate in USD to support the response.

Search Results:
{context}
"""

    try:
        response = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Groq Error while summarizing: {str(e)}"

# ---- Flask Setup ----
app = Flask(__name__)

@app.route('/get_disaster_summary', methods=['POST'])
def get_disaster_summary():
    data = request.get_json()
    query = data.get("query")

    if not query:
        return jsonify({"error": "Missing 'query' in JSON body"}), 400

    search_results = search_disaster_topic(query)
    summary = summarize_search_results(search_results, query)

    return jsonify({"summary": summary})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
