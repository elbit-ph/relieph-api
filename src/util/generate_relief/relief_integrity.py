import json
from .gemini import model, json_template



def relief_data(response):
    jsonify_prompt = f"I need you to modify the keys in this JSON object {response}. Output strictly just the JSON object following this format {json_template}. Make sure to output a string in the"
    relief_data_json = model.generate_content([jsonify_prompt])

    data = relief_data_json.text.lstrip('```json')
    data = data.rstrip('```')

    relief_data_dict = json.loads(data) 
    print(relief_data_dict)
    return relief_data_dict

