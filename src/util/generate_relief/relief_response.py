from .gemini import model, json_template

def response(disaster_type, headline_title, article_date_posted, context):
    generate_prompt = f"disaster type: {disaster_type}\n headline title: {headline_title}\n article date posted: {article_date_posted}\n article content: {context} \n\n Generate a JSON object representing a relief effort for this disaster.  Ensure the JSON is well-formed. It should include the following:\n Possible Relief Effort Title (be creative in creating relief effort title)\n Relief Effort Description\n Monetary Goal for Donation (use just integer)\n\n List of inkind donation:\n Name of item (think of relevent physical item for the relief effort based on article content)\n Description of item or specification or further details\n Quantity of such in kind donation\n Deployment date of relief effort. Strictly output just the JSON object.  Don't include anything else as besides the actualy JSON object I would parse this text. There should be NO null fields. Strictly COMPLETE all fields with value. Don't add null in monetary goal, quantity and deployment. The monetary goal and quantity should be strictly integer values (5000-1000000 decide the monetary goal based on the article context) and deployment date should be valid date format (YYYY-MM-DD). Items in inkind should not be money. \n\n Make sure to follow this format:\n {json_template}"
    
    relief_response = model.generate_content([generate_prompt])
    data = relief_response.text.lstrip('```json')
    data = data.rstrip('```')

    return data