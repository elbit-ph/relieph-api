import re
import ast
import logging
from .gemini import model

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def data_handling(generated_relief_data):
    for i, data in enumerate(generated_relief_data):
        data['urgency'] = -1

def data_integrity(data):
    pattern = r'\[.*?\]'
    
    match = re.search(pattern, data)
    extracted_list = match.group(0)
    return extracted_list

def generated_relief_urgency(generated_relief_data):
    prompt = "Given this list of relief effort, output a python list in equivalent length containing just numbers (1 - number of relief effort) and rank them accordingly based on perceived urgency of such relief effort. Strictly output only the python list containing the rankings of the relief effort.\n\n"

    for data in generated_relief_data:
        prompt += f"Relief Effort Title: {data['relief_title']}\n Description: {data['description']}\n News Headline Title: {data['headline_title']}\n"

    prompt += f"\nStrictly output just a python list containing numbers that represent the ranking of each relief effort.The ranking values should only range from 1 up to the number of relief effort given. Do not include anything else."

    try:
        response = model.generate_content([prompt])
        processed_response = data_integrity(response.text)
        response_list = ast.literal_eval(processed_response) 
    except Exception as e:
        logger.info("Relief Effort Ranking Failed!")
        data_handling(generated_relief_data)
        return generated_relief_data

    for i, data in enumerate(generated_relief_data):
        data['urgency'] = response_list[i]

    logger.info("Relief Effort Ranking Success!")
    return generated_relief_data
