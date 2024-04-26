import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

generation_config = {
  "temperature": 0.9,
  "top_p": 1,
  "top_k": 1,
  "max_output_tokens": 2048,
}

safety_settings = [
  {
    "category": "HARM_CATEGORY_HARASSMENT",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
  {
    "category": "HARM_CATEGORY_HATE_SPEECH",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
  {
    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
  {
    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
  },
]

model = genai.GenerativeModel(
  model_name="gemini-1.0-pro",
  generation_config=generation_config,
  safety_settings=safety_settings
)

headline_title = "Two dead, over 400,000 affected by 'habagat' due to 'Hanna', 'Goring'"
disaster_type = "Typhoon"
article_date_posted = "Sunday 3, September 2023"

context = "MANILA, Philippines — Two people reportedly died and over 400,000 individuals were affected by the southwest monsoon enhanced by cyclones Goring and Hanna, the National Disaster Risk Reduction and Management Council reported Sunday. The NDRRMC said in its latest report that it is validating the deaths reported in the Cordillera Administrative Region and in Western Visayas. One person was reportedly injured and one was reportedly missing.  The weather disturbances affected around 418,000 individuals in eight regions, with 52,072 people forced to flee their homes.  The combined effects of Goring, Hanna, and the southwest monsoon also wreaked havoc in the agricultural sector. According to the NDRRMC, around 10,196 farmers and fisherfolk were affected. Damage to crops and agriculture infrastructure reached at least P421.19 million.  Meanwhile, the initial damage to infrastructure was estimated at around P130 million. The government has so far provided P20.9 million in assistance to affected residents. Hanna—the country’s eighth cyclone this year—continues to threaten the northern tip of the Philippines and enhance the southwest monsoon. It may exit the Philippine Area of Responsibility late Sunday or early Monday. — Gaea Katreena Cabico"

generate_prompt = f"disaster type: {disaster_type}\n headline title: {headline_title}\n article date posted: {article_date_posted}\n\n Generate a JSON object representing a relief effort for this disaster.  Ensure the JSON is well-formed. It should include the following:\n Possible Relief Effort Title\n Relief Effort Description\n Monetary Goal for Donation (use just integer but consider that it is in philippine peso value)\n\n List of inkind donation:\n Name of item\n Description of item or specification or further details\n Quantity of such in kind donation\n Deployment date of relief effort. Strictly output just the JSON object"

response = model.generate_content([generate_prompt])

print(response.text)



json_template = '''
{
    "relief_title": "",
    "description": "",
    "headline_title": "",
    "date_posted": "",
    "link": "",
    "monetary_goal": "",
    "inkind_donation": [
        {
            "item": "",
            "item_desc": "",
            "quantity": ""
        }
    ],
    "deployment_date": "",
}
'''

jsonify_prompt = f"I need you to modify the keys in this JSON object {response}. Output strictly just the JSON object following this format {json_template}. I just want to maintain data integrity for saving it to the database"

json_response = model.generate_content([jsonify_prompt])

print(json_response.text)
